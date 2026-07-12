/**
 * Owns the customer chat surface's entire session lifecycle: resolve
 * (space, persona) from `?space=`/`?persona=` URL params or a picker sheet,
 * provision a session, stream chat turns, and keep the message list +
 * avatar state in sync with the SSE frame sequence.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api";
import { useSpaceSocket } from "@/hooks/useSpaceSocket";
import type { AvatarState } from "@/lib/types";
import type { LanguageCode } from "@/components/shared/LangToggle";
import type { ChatMessage, ChatSseFrame, PersonaRosterItem, SessionCreateResponse } from "./types";
import { readSseFrames } from "./sse";

export type ChatSessionStatus =
  | "loading_roster"
  | "roster_error"
  | "picking"
  | "provisioning"
  | "provision_error"
  | "ready";

const KNOWN_LANGUAGES: LanguageCode[] = ["en", "hi", "gu"];

function asLanguage(value: string | null | undefined): LanguageCode | null {
  return value && (KNOWN_LANGUAGES as string[]).includes(value) ? (value as LanguageCode) : null;
}

function newId(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}${Date.now().toString(36)}`;
}

const IDLE_AFTER_TURN_MS = 4000;

export interface UseChatSessionResult {
  status: ChatSessionStatus;
  roster: PersonaRosterItem[] | undefined;
  rosterLoading: boolean;
  retryRoster: () => void;
  pickPersona: (personaId: string, language: LanguageCode) => void;
  persona: PersonaRosterItem | null;
  spaceId: string | null;
  sessionId: string | null;
  language: LanguageCode;
  setLanguage: (lang: LanguageCode) => void;
  messages: ChatMessage[];
  avatarState: AvatarState;
  sending: boolean;
  sendMessage: (text: string) => void;
  provisionError: string | null;
  retryProvision: () => void;
  lastAuditRef: string | null;
}

export function useChatSession(): UseChatSessionResult {
  const [searchParams] = useSearchParams();
  const urlSpace = searchParams.get("space");
  const urlPersona = searchParams.get("persona");
  const urlLanguage = asLanguage(searchParams.get("language"));

  const rosterQuery = useQuery({
    queryKey: ["chat-personas-roster"],
    queryFn: () => apiGet<PersonaRosterItem[]>("/personas"),
  });

  const [spaceId, setSpaceId] = useState<string | null>(urlSpace);
  const spaceCreateAttempted = useRef(false);

  useEffect(() => {
    if (spaceId || spaceCreateAttempted.current) return;
    spaceCreateAttempted.current = true;
    apiPost<{ space_id: string }>("/spaces")
      .then((res) => setSpaceId(res.space_id))
      .catch(() => {
        spaceCreateAttempted.current = false;
      });
  }, [spaceId]);

  const [personaId, setPersonaId] = useState<string | null>(urlPersona);
  const [language, setLanguage] = useState<LanguageCode>(urlLanguage ?? "en");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [avatarState, setAvatarState] = useState<AvatarState>("idle");
  const [sending, setSending] = useState(false);
  const [provisionError, setProvisionError] = useState<string | null>(null);
  const [provisionAttempt, setProvisionAttempt] = useState(0);
  const [lastAuditRef, setLastAuditRef] = useState<string | null>(null);

  const provisionKeyRef = useRef<string | null>(null);
  const pendingUserTextRef = useRef<string | null>(null);
  const idleTimerRef = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (idleTimerRef.current !== null) window.clearTimeout(idleTimerRef.current);
    },
    []
  );

  const persona = rosterQuery.data?.find((p) => p.id === personaId) ?? null;

  /** Applies one SSE frame to the live message list + avatar state. Shared
   * between the greeting (a plain array) and a live chat turn (a stream) so
   * both paths render identically. */
  const ingestFrame = useCallback((frame: ChatSseFrame) => {
    if (frame.type === "avatar") {
      setAvatarState(frame.state);
      return;
    }
    if (frame.type === "token") {
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === "companion" && last.streaming) {
          const updated = { ...last, text: (last.text ?? "") + frame.text };
          return [...prev.slice(0, -1), updated];
        }
        return [
          ...prev,
          { id: newId("msg"), role: "companion", ts: new Date().toISOString(), text: frame.text, streaming: true },
        ];
      });
      return;
    }
    if (frame.type === "card") {
      setMessages((prev) => {
        const closed = prev.map((m, i) =>
          i === prev.length - 1 && m.role === "companion" && m.streaming ? { ...m, streaming: false } : m
        );
        return [...closed, { id: newId("card"), role: "companion", ts: new Date().toISOString(), card: frame.card }];
      });
      return;
    }
    // done
    setLastAuditRef(frame.audit_ref);
    if (frame.error) setAvatarState("concerned");
    if (idleTimerRef.current !== null) window.clearTimeout(idleTimerRef.current);
    idleTimerRef.current = window.setTimeout(() => setAvatarState("idle"), IDLE_AFTER_TURN_MS);
    // Read the ref BEFORE setMessages: the updater runs lazily during the
    // next render, after this function has already nulled the ref.
    const retryText = pendingUserTextRef.current ?? undefined;
    pendingUserTextRef.current = null;
    setMessages((prev) => {
      const closed = prev.map((m, i) =>
        i === prev.length - 1 && m.role === "companion" && m.streaming ? { ...m, streaming: false } : m
      );
      if (frame.error) {
        // Only replies from THIS turn count — scan after the last user
        // message, else the greeting suppresses every later error bubble.
        const lastUserIndex = closed.reduce((acc, m, i) => (m.role === "user" ? i : acc), -1);
        const hadReply = closed
          .slice(lastUserIndex + 1)
          .some((m) => m.role === "companion" && (m.text ?? "").trim().length > 0);
        if (!hadReply) {
          return [
            ...closed,
            {
              id: newId("err"),
              role: "companion",
              ts: new Date().toISOString(),
              error: true,
              retryText,
            },
          ];
        }
      }
      return closed;
    });
  }, []);

  // -- provisioning --------------------------------------------------------

  useEffect(() => {
    if (!spaceId || !personaId) return;
    const key = `${spaceId}:${personaId}:${provisionAttempt}`;
    if (provisionKeyRef.current === key) return;
    provisionKeyRef.current = key;

    let cancelled = false;
    setProvisionError(null);
    const lang = urlLanguage ?? (asLanguage(persona?.language) ?? language);

    apiPost<SessionCreateResponse>(`/spaces/${spaceId}/sessions`, { persona_id: personaId, language: lang })
      .then((res) => {
        if (cancelled) return;
        setSessionId(res.session_id);
        setLanguage(lang);
        for (const frame of res.greeting) ingestFrame(frame);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        provisionKeyRef.current = null;
        setProvisionError(err instanceof Error ? err.message : "Could not start a session.");
      });

    return () => {
      cancelled = true;
    };
    // persona/language intentionally excluded — captured once at provision time via urlLanguage/persona.language.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [spaceId, personaId, provisionAttempt, ingestFrame]);

  // Real-time nudge feed (Task 13): a matching persona's `nudge.created`
  // event is woven into the thread as a live `nudge` card, the same way an
  // orchestrator-emitted card would be — proactive nudges are part of the
  // Track 1 requirement, not just a request/response feature.
  const { subscribe } = useSpaceSocket(spaceId);
  useEffect(() => {
    if (!sessionId) return undefined;
    return subscribe("nudge.created", (nudge) => {
      if (nudge.persona_id !== personaId) return;
      setMessages((prev) => [
        ...prev,
        {
          id: newId("nudge"),
          role: "companion",
          ts: new Date().toISOString(),
          card: { card_type: "nudge", title: nudge.title, body: nudge.body, kind: nudge.kind, intent: nudge.intent },
        },
      ]);
    });
  }, [subscribe, sessionId, personaId]);

  const pickPersona = useCallback((id: string, lang: LanguageCode) => {
    setLanguage(lang);
    setPersonaId(id);
  }, []);

  const retryProvision = useCallback(() => {
    setProvisionAttempt((n) => n + 1);
  }, []);

  const retryRoster = useCallback(() => {
    void rosterQuery.refetch();
  }, [rosterQuery]);

  const sendMessage = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || !sessionId || sending) return;
      pendingUserTextRef.current = trimmed;
      setMessages((prev) => [...prev, { id: newId("msg"), role: "user", ts: new Date().toISOString(), text: trimmed }]);
      setSending(true);
      setAvatarState("thinking");
      if (idleTimerRef.current !== null) window.clearTimeout(idleTimerRef.current);

      fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify({ session_id: sessionId, message: trimmed, language }),
      })
        .then((response) => {
          if (!response.ok) throw new Error(`chat failed: ${response.status}`);
          return readSseFrames(response, ingestFrame);
        })
        .catch(() => {
          setMessages((prev) => [
            ...prev,
            {
              id: newId("err"),
              role: "companion",
              ts: new Date().toISOString(),
              error: true,
              retryText: trimmed,
            },
          ]);
        })
        .finally(() => setSending(false));
    },
    [sessionId, sending, language, ingestFrame]
  );

  let status: ChatSessionStatus;
  if (sessionId) status = "ready";
  else if (provisionError) status = "provision_error";
  else if (personaId && spaceId) status = "provisioning";
  else if (rosterQuery.isLoading) status = "loading_roster";
  else if (rosterQuery.isError) status = "roster_error";
  else status = "picking";

  return {
    status,
    roster: rosterQuery.data,
    rosterLoading: rosterQuery.isLoading,
    retryRoster,
    pickPersona,
    persona,
    spaceId,
    sessionId,
    language,
    setLanguage,
    messages,
    avatarState,
    sending,
    sendMessage,
    provisionError,
    retryProvision,
    lastAuditRef,
  };
}
