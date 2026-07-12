import { useEffect, useRef } from "react";
import { formatDate } from "@/lib/format";
import { Avatar } from "@/components/shared/Avatar";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { TypingIndicator } from "@/components/chat/TypingIndicator";
import { makeT, type LanguageCode } from "@/lib/i18n";
import type { AvatarState } from "@/lib/types";
import type { ChatMessage } from "@/routes/customer/types";

export interface MessageListProps {
  messages: ChatMessage[];
  avatarState: AvatarState;
  sending: boolean;
  onRetry: (text: string) => void;
  sessionId: string | null;
  onSendMessage: (text: string) => void;
  onOpenAudit: () => void;
  language?: LanguageCode;
  companionBubbleClass?: string;
  userBubbleClass?: string;
}

function dayLabel(iso: string, t: ReturnType<typeof makeT>): string {
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return "";
  const today = new Date();
  if (parsed.toDateString() === today.toDateString()) return t("chat.today");
  return formatDate(iso);
}

/** True once the current turn's companion text has started streaming — the
 * moment it flips, the typing indicator hands off to the real bubble. */
function turnHasStarted(messages: ChatMessage[]): boolean {
  const last = messages[messages.length - 1];
  return Boolean(last && last.role === "companion" && last.streaming);
}

export function MessageList({
  messages,
  avatarState,
  sending,
  onRetry,
  sessionId,
  onSendMessage,
  onOpenAudit,
  language = "en",
  companionBubbleClass,
  userBubbleClass,
}: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);
  const t = makeT(language);

  // Only chase the viewport down when the user just sent a turn — that's
  // when they need to see their own message plus the typing indicator. A
  // streaming companion reply (or a card/nudge landing after it) must NOT
  // pull the viewport along, else the greeting/reply is never readable from
  // its own top; the user scrolls at their own pace once it starts.
  const lastMessage = messages[messages.length - 1];
  const lastIsUserTurn = lastMessage?.role === "user";
  useEffect(() => {
    if (!lastIsUserTurn) return;
    endRef.current?.scrollIntoView({ block: "end" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages.length, sending, lastIsUserTurn]);

  const showTyping = sending && !turnHasStarted(messages);
  let lastDay = "";

  return (
    <div className="space-y-4 px-4 py-4">
      {messages.map((message) => {
        const label = dayLabel(message.ts, t);
        const showDivider = label !== lastDay;
        lastDay = label;
        return (
          <div key={message.id} className="space-y-4">
            {showDivider && (
              <div className="flex items-center justify-center">
                <span className="rounded-full bg-neutral-100 px-3 py-1 text-caption font-medium text-neutral-500">
                  {label}
                </span>
              </div>
            )}
            <MessageBubble
              message={message}
              onRetry={onRetry}
              sessionId={sessionId}
              onSendMessage={onSendMessage}
              onOpenAudit={onOpenAudit}
              sending={sending}
              language={language}
              companionBubbleClass={companionBubbleClass}
              userBubbleClass={userBubbleClass}
            />
          </div>
        );
      })}

      {showTyping && (
        <div className="flex items-center gap-2">
          <Avatar state={avatarState === "idle" ? "thinking" : avatarState} size={28} />
          <TypingIndicator />
        </div>
      )}

      <div ref={endRef} />
    </div>
  );
}
