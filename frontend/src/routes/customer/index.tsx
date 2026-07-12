/**
 * The customer chat surface (`/app`) — WealthMitra's judge-facing
 * centerpiece. Renders the full conversational loop inside the IDBI mobile
 * shell: SSE-streamed replies with a live avatar, rich in-stream cards,
 * persona-aware localized prompt chips, mid-conversation language switch,
 * optional voice in/out, and the "why this number" audit drawer.
 */
import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import { PhoneFrame } from "@/components/shared/PhoneFrame";
import { Button } from "@/components/ui/button";
import { ChatHeader, type AppTab } from "@/components/chat/ChatHeader";
import { MessageList } from "@/components/chat/MessageList";
import { ChipRow } from "@/components/chat/ChipRow";
import { ChatInput } from "@/components/chat/ChatInput";
import { AuditDrawer } from "@/components/chat/AuditDrawer";
import { useSpeechOutput } from "@/components/chat/useVoice";
import { t } from "@/lib/i18n";
import { PersonaPicker } from "./PersonaPicker";
import { PersonaSwitcher } from "./PersonaSwitcher";
import { JudgePanel } from "./JudgePanel";
import { chipsFor } from "./chips";
import { useChatSession } from "./useChatSession";
import { useSpaceLeads } from "./useSpaceLeads";
import { CustomerDashboard } from "./dashboard";

export type { AppTab };

function ChatSkeleton() {
  return (
    <div className="animate-pulse space-y-4 px-4 py-4" aria-hidden="true">
      <div className="flex justify-start">
        <div className="h-16 w-3/5 rounded-lg rounded-tl-sm bg-neutral-200" />
      </div>
      <div className="flex justify-end">
        <div className="h-10 w-2/5 rounded-lg rounded-tr-sm bg-neutral-100" />
      </div>
      <div className="flex justify-start">
        <div className="h-40 w-11/12 rounded-lg bg-neutral-100" />
      </div>
    </div>
  );
}

export default function CustomerChat() {
  const [searchParams] = useSearchParams();
  // Inside the /present stage the phone is iframed with `?embedded=1`; there
  // the auto coachmark would overlay the greeting and the stage already has
  // its own guided walkthrough, so suppress the auto-tour there.
  const embedded = searchParams.get("embedded") === "1";
  const session = useChatSession();
  const { count: leadCount, hasLeads } = useSpaceLeads(session.spaceId);
  const speech = useSpeechOutput();
  const [auditOpen, setAuditOpen] = useState(false);
  const [tab, setTab] = useState<AppTab>("chat");
  // The blocking first-run picker (session.status === "picking") stays
  // driven entirely by session state — this only controls the voluntary,
  // dismissible "switch customer" reopen (requirement 7: never re-force the
  // full sheet once a persona is already active).
  const [switcherOpen, setSwitcherOpen] = useState(false);

  // Speak each companion reply once, only after its stream closes — reading
  // half a sentence aloud mid-stream sounds broken, not conversational.
  const lastSpokenRef = useRef<string | null>(null);
  useEffect(() => {
    if (!speech.enabled) return;
    const lastReply = [...session.messages]
      .reverse()
      .find((m) => m.role === "companion" && !m.streaming && (m.text ?? "").trim().length > 0);
    if (lastReply && lastReply.id !== lastSpokenRef.current) {
      lastSpokenRef.current = lastReply.id;
      speech.speak(lastReply.text ?? "", session.language);
    }
  }, [session.messages, session.language, speech]);

  const chips = session.persona ? chipsFor(session.persona.id, session.language) : [];
  const showChat = session.status === "ready";
  const isBlockingPicker =
    session.status === "picking" || session.status === "loading_roster" || session.status === "roster_error";

  return (
    <div
      className={
        embedded
          ? "flex justify-center px-6 py-8"
          : "flex flex-col items-center gap-6 px-6 py-8 lg:flex-row lg:items-start lg:justify-center"
      }
    >
      {/* The judge's "toggle between customers" control (Fix 2) — outside the
          phone entirely, never shown in the /present iframe (one persona per
          stage there). Renders before the phone so it lands as the left
          column on desktop and a horizontal strip above the phone on
          narrow viewports. */}
      {!embedded && (
        <PersonaSwitcher
          roster={session.roster}
          activePersonaId={session.persona?.id ?? null}
          language={session.language}
          onPick={session.pickPersona}
        />
      )}

      <PhoneFrame headerTitle="IDBI Bank · WealthMitra" activeNav="wealthmitra">
        <div className="flex h-full flex-col">
          {showChat && session.persona ? (
            <>
              <ChatHeader
                personaName={session.persona.name}
                avatarState={session.avatarState}
                language={session.language}
                onLanguageChange={session.setLanguage}
                speechSupported={speech.supported}
                speechEnabled={speech.enabled}
                onToggleSpeech={speech.toggle}
                onSwitchPersona={() => setSwitcherOpen(true)}
                tab={tab}
                onTabChange={setTab}
                autoTour={false}
              />

              {tab === "chat" ? (
                <>
                  <div className="min-h-0 flex-1 overflow-y-auto">
                    <MessageList
                      messages={session.messages}
                      avatarState={session.avatarState}
                      sending={session.sending}
                      onRetry={session.sendMessage}
                      sessionId={session.sessionId}
                      onSendMessage={session.sendMessage}
                      onOpenAudit={() => setAuditOpen(true)}
                      language={session.language}
                    />
                  </div>

                  <div className="shrink-0 border-t border-neutral-200 bg-neutral-0">
                    <ChipRow chips={chips} onPick={session.sendMessage} disabled={session.sending} />
                    <ChatInput language={session.language} disabled={session.sending} onSend={session.sendMessage} />
                  </div>
                </>
              ) : (
                <div className="min-h-0 flex-1 overflow-y-auto">
                  {session.sessionId && (
                    <CustomerDashboard
                      sessionId={session.sessionId}
                      spaceId={session.spaceId}
                      personaId={session.persona.id}
                      language={session.language}
                    />
                  )}
                </div>
              )}
            </>
          ) : session.status === "provision_error" ? (
            <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 text-center">
              <span className="flex size-11 items-center justify-center rounded-full bg-danger-50 text-danger-600">
                <AlertTriangle size={20} strokeWidth={1.75} />
              </span>
              <p className="text-body-sm font-medium text-neutral-700">{t(session.language, "chat.couldNotStart")}</p>
              <p className="max-w-xs text-caption text-neutral-600">{t(session.language, "chat.couldNotStartDesc")}</p>
              <Button size="touch" variant="outline" onClick={session.retryProvision}>
                {t(session.language, "chat.tryAgain")}
              </Button>
            </div>
          ) : (
            <ChatSkeleton />
          )}
        </div>
      </PhoneFrame>

      {/* Judge/evaluator cockpit — audit trail + RM-desk jump. Judge-only
          demo affordances, never part of what a real customer would see, so
          it lives beside the phone rather than inside it, and never renders
          in the /present iframe (one persona per stage there). */}
      {!embedded && (
        <JudgePanel
          spaceId={session.spaceId}
          sessionId={session.sessionId}
          hasLeads={hasLeads}
          leadCount={leadCount}
          language={session.language}
          onOpenAudit={() => setAuditOpen(true)}
        />
      )}

      <PersonaPicker
        open={isBlockingPicker}
        loading={session.rosterLoading}
        error={session.status === "roster_error"}
        roster={session.roster}
        onRetry={session.retryRoster}
        onPick={session.pickPersona}
        mode="initial"
        language={session.language}
      />

      {/* Voluntary switch: same picker, dismissible, opened from the header
       * avatar — never blocks once a persona is already active. */}
      <PersonaPicker
        open={switcherOpen}
        loading={session.rosterLoading}
        error={session.status === "roster_error"}
        roster={session.roster}
        onRetry={session.retryRoster}
        onPick={(id, lang) => {
          session.pickPersona(id, lang);
          setSwitcherOpen(false);
        }}
        mode="switch"
        onDismiss={() => setSwitcherOpen(false)}
        language={session.language}
      />

      <AuditDrawer sessionId={session.sessionId} open={auditOpen} onOpenChange={setAuditOpen} language={session.language} />
    </div>
  );
}
