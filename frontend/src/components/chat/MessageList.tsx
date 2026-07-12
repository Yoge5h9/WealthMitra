import { useEffect, useRef } from "react";
import { formatDate } from "@/lib/format";
import { Avatar } from "@/components/shared/Avatar";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { TypingIndicator } from "@/components/chat/TypingIndicator";
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
}

function dayLabel(iso: string): string {
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return "";
  const today = new Date();
  if (parsed.toDateString() === today.toDateString()) return "Today";
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
}: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length, sending]);

  const showTyping = sending && !turnHasStarted(messages);
  let lastDay = "";

  return (
    <div className="space-y-4 px-4 py-4">
      {messages.map((message) => {
        const label = dayLabel(message.ts);
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
