/**
 * The customer chat surface (`/app`) — WealthMitra's judge-facing
 * centerpiece. Renders the full conversational loop inside the IDBI mobile
 * shell: SSE-streamed replies with a live avatar, rich in-stream cards,
 * persona-aware localized prompt chips, mid-conversation language switch,
 * optional voice in/out, and the "why this number" audit drawer.
 */
import { useEffect, useRef, useState } from "react";
import { AlertTriangle, LayoutDashboard, MessageCircle, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { PhoneFrame } from "@/components/shared/PhoneFrame";
import { Button } from "@/components/ui/button";
import { ChatHeader } from "@/components/chat/ChatHeader";
import { MessageList } from "@/components/chat/MessageList";
import { ChipRow } from "@/components/chat/ChipRow";
import { ChatInput } from "@/components/chat/ChatInput";
import { AuditDrawer } from "@/components/chat/AuditDrawer";
import { useSpeechOutput } from "@/components/chat/useVoice";
import { PersonaPicker } from "./PersonaPicker";
import { chipsFor } from "./chips";
import { useChatSession } from "./useChatSession";
import { CustomerDashboard } from "./dashboard";

type AppTab = "chat" | "dashboard";

/** Segmented Chat/Dashboard switch (Task 16) — the Dashboard tab is a
 * sibling view inside the same `/app` shell, not a route change, so the
 * session/persona/space context never has to re-provision. */
function AppTabBar({ tab, onChange }: { tab: AppTab; onChange: (tab: AppTab) => void }) {
  const tabs: { id: AppTab; label: string; icon: typeof MessageCircle }[] = [
    { id: "chat", label: "Chat", icon: MessageCircle },
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  ];
  return (
    <div className="flex shrink-0 gap-1 border-b border-neutral-200 bg-neutral-0 px-2 pt-2" role="tablist">
      {tabs.map(({ id, label, icon: Icon }) => {
        const active = tab === id;
        return (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(id)}
            className={cn(
              "flex min-h-11 flex-1 items-center justify-center gap-1.5 rounded-t-sm border-b-2 px-3 text-body-sm font-medium transition-colors duration-[var(--motion-micro)] ease-out focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]",
              active ? "border-structural-600 text-structural-700" : "border-transparent text-neutral-500 hover:text-neutral-700"
            )}
          >
            <Icon size={16} strokeWidth={1.75} aria-hidden="true" />
            {label}
          </button>
        );
      })}
    </div>
  );
}

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
  const session = useChatSession();
  const speech = useSpeechOutput();
  const [auditOpen, setAuditOpen] = useState(false);
  const [tab, setTab] = useState<AppTab>("chat");

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

  return (
    <div className="flex justify-center px-6 py-8">
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
                onOpenAudit={() => setAuditOpen(true)}
              />

              <AppTabBar tab={tab} onChange={setTab} />

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
                    />
                  </div>

                  <div className="shrink-0 border-t border-neutral-200 bg-neutral-0">
                    <ChipRow chips={chips} onPick={session.sendMessage} disabled={session.sending} />
                    <ChatInput language={session.language} disabled={session.sending} onSend={session.sendMessage} />
                    <button
                      type="button"
                      onClick={() => setAuditOpen(true)}
                      className="flex min-h-11 w-full items-center gap-2 border-t border-neutral-200 px-4 text-left text-caption text-neutral-600 transition-colors duration-[var(--motion-micro)] ease-out hover:text-structural-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
                    >
                      <ShieldCheck size={16} strokeWidth={1.75} className="shrink-0 text-structural-600" aria-hidden="true" />
                      Every figure computed from your data · tap to see why
                    </button>
                  </div>
                </>
              ) : (
                <div className="min-h-0 flex-1 overflow-y-auto">
                  {session.sessionId && (
                    <CustomerDashboard
                      sessionId={session.sessionId}
                      spaceId={session.spaceId}
                      personaId={session.persona.id}
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
              <p className="text-body-sm font-medium text-neutral-700">Couldn't start your conversation</p>
              <p className="max-w-xs text-caption text-neutral-600">
                WealthMitra couldn't reach the bank right now. Nothing was changed — try again.
              </p>
              <Button size="touch" variant="outline" onClick={session.retryProvision}>
                Try again
              </Button>
            </div>
          ) : (
            <ChatSkeleton />
          )}
        </div>
      </PhoneFrame>

      <PersonaPicker
        open={session.status === "picking" || session.status === "loading_roster" || session.status === "roster_error"}
        loading={session.rosterLoading}
        error={session.status === "roster_error"}
        roster={session.roster}
        onRetry={session.retryRoster}
        onPick={session.pickPersona}
      />

      <AuditDrawer sessionId={session.sessionId} open={auditOpen} onOpenChange={setAuditOpen} />
    </div>
  );
}
