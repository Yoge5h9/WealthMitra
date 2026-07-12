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

/**
 * Per-tab chat persistence (requirement: revisiting `/app` — or switching
 * back to a persona — must not wipe the conversation). Keyed by
 * `(spaceId, personaId)` so every demo customer keeps their own thread;
 * `sessionStorage` is the right lifetime here — per-tab, cleared when the
 * judge closes it, never a cross-session leak between demo runs.
 */
interface PersistedChat {
  messages: ChatMessage[];
  language: LanguageCode;
}

function persistKey(spaceId: string, personaId: string): string {
  return `wm_chat_${spaceId}_${personaId}`;
}

function loadPersistedChat(spaceId: string, personaId: string): PersistedChat | null {
  try {
    const raw = window.sessionStorage.getItem(persistKey(spaceId, personaId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<PersistedChat>;
    if (!Array.isArray(parsed.messages)) return null;
    return { messages: parsed.messages, language: asLanguage(parsed.language) ?? "en" };
  } catch {
    return null;
  }
}

function savePersistedChat(spaceId: string, personaId: string, data: PersistedChat): void {
  try {
    window.sessionStorage.setItem(persistKey(spaceId, personaId), JSON.stringify(data));
  } catch {
    // sessionStorage unavailable/full — persistence is best-effort for a demo, never fatal.
  }
}

/**
 * Which persona/language was last active, independent of any particular
 * (space, persona) thread — this is what lets a plain reload of `/app` (no
 * URL params at all) come back to the same customer instead of re-showing
 * the first-run picker every time.
 */
const ACTIVE_PERSONA_KEY = "wm_active_persona";

interface ActivePersona {
  personaId: string;
  language: LanguageCode;
}

function loadActivePersona(): ActivePersona | null {
  try {
    const raw = window.sessionStorage.getItem(ACTIVE_PERSONA_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<ActivePersona>;
    if (!parsed.personaId) return null;
    return { personaId: parsed.personaId, language: asLanguage(parsed.language) ?? "en" };
  } catch {
    return null;
  }
}

function saveActivePersona(data: ActivePersona): void {
  try {
    window.sessionStorage.setItem(ACTIVE_PERSONA_KEY, JSON.stringify(data));
  } catch {
    // best-effort, same rationale as savePersistedChat above.
  }
}

/** Well-known shared space every plain `/app` and `/rm` visit lands in when
 * no `?space=` is given — so a lead created in chat reaches the RM desk in
 * another tab without either side minting its own private space. `/present`
 * always passes an explicit `?space=`, which still wins below. */
const DEFAULT_SPACE_ID = "default";
const NEW_TO_IDBI_PERSONA: PersonaRosterItem = {
  id: "new_to_idbi", name: "New to IDBI", age: 0, city: "", segment: "starting profile", language: "en", avatar: "", story: "No banking history yet",
};

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

  // `?space=` (used by /present to isolate each judge's iframe pair) wins;
  // otherwise every plain `/app` and `/rm` visit shares the well-known
  // "default" space so a lead created in chat reaches the RM desk.
  const [spaceId] = useState<string | null>(urlSpace ?? DEFAULT_SPACE_ID);

  // Resolve the active persona once at mount: `?persona=` (highest — /present
  // pins one persona per iframe) → last-persisted persona for this tab →
  // null (genuine first visit, the blocking picker takes over).
  const [persistedActive] = useState<ActivePersona | null>(() => loadActivePersona());
  const [personaId, setPersonaId] = useState<string | null>(urlPersona ?? persistedActive?.personaId ?? null);
  const [language, setLanguage] = useState<LanguageCode>(
    urlLanguage ?? persistedActive?.language ?? "en"
  );
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

  const persona = personaId === NEW_TO_IDBI_PERSONA.id
    ? NEW_TO_IDBI_PERSONA
    : rosterQuery.data?.find((p) => p.id === personaId) ?? null;

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
        // Rehydrate this persona's persisted thread instead of re-greeting —
        // switching back to a customer (or reopening the tab) should resume
        // the conversation, not restart it.
        const persisted = loadPersistedChat(spaceId, personaId);
        if (persisted && persisted.messages.length > 0) {
          setMessages(persisted.messages);
          setLanguage(persisted.language);
        } else {
          setMessages([]);
          setLanguage(lang);
          for (const frame of res.greeting) ingestFrame(frame);
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        provisionKeyRef.current = null;
        setProvisionError(err instanceof Error ? err.message : "Could not start a session.");
      });

    return () => {
      cancelled = true;
      // React StrictMode (dev) tears this effect down and immediately re-runs
      // it. Release the provision guard so the re-run actually re-provisions —
      // otherwise it no-ops on the matching key while this run's result is
      // discarded by `cancelled`, and the greeting never lands (empty chat).
      if (provisionKeyRef.current === key) provisionKeyRef.current = null;
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

  // Persist the active persona's thread on every change — a continuous,
  // cheap best-effort save rather than a single point the switch could miss.
  useEffect(() => {
    if (!spaceId || !personaId || messages.length === 0) return;
    savePersistedChat(spaceId, personaId, { messages, language });
  }, [spaceId, personaId, messages, language]);

  // Remember which persona/language is active independent of any one
  // thread — this is what a plain reload of `/app` (no URL params at all)
  // reads back so it resumes the same customer instead of re-blocking on
  // the first-run picker.
  useEffect(() => {
    if (!personaId) return;
    saveActivePersona({ personaId, language });
  }, [personaId, language]);

  const pickPersona = useCallback(
    (id: string, lang: LanguageCode) => {
      // Re-picking the already-active persona (e.g. reopening the switcher
      // and tapping the same customer) is a no-op — don't reset a live thread.
      if (id === personaId) return;
      // A previously-visited persona resumes in whatever language their
      // thread was last left in, not whatever language happens to be active
      // right now — switching customers shouldn't also silently retranslate them.
      const persisted = spaceId ? loadPersistedChat(spaceId, id) : null;
      setSessionId(null); // forces the provisioning skeleton while the new session resolves
      setMessages([]);
      setLanguage(persisted?.language ?? lang);
      setPersonaId(id);
    },
    [spaceId, personaId]
  );

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
