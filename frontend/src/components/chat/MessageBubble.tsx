import { AlertTriangle, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { CardRouter } from "@/components/chat/cards/CardRouter";
import { t, type LanguageCode } from "@/lib/i18n";
import type { ChatMessage } from "@/routes/customer/types";

const timeFormatter = new Intl.DateTimeFormat("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false });

function formatTime(iso: string): string {
  const parsed = new Date(iso);
  return Number.isNaN(parsed.getTime()) ? "" : timeFormatter.format(parsed);
}

export interface MessageBubbleProps {
  message: ChatMessage;
  onRetry?: (text: string) => void;
  sessionId?: string | null;
  onSendMessage?: (text: string) => void;
  onOpenAudit?: () => void;
  sending?: boolean;
  language?: LanguageCode;
  companionBubbleClass?: string;
  userBubbleClass?: string;
}

export function MessageBubble({
  message,
  onRetry,
  sessionId,
  onSendMessage,
  onOpenAudit,
  sending,
  language = "en",
  companionBubbleClass,
  userBubbleClass,
}: MessageBubbleProps) {
  const isUser = message.role === "user";

  if (message.error) {
    return (
      <div className="flex justify-start">
        <div className="flex max-w-[85%] flex-col gap-2 rounded-lg border border-danger-200 bg-danger-50 px-4 py-3">
          <div className="flex items-center gap-2 text-danger-700">
            <AlertTriangle size={16} strokeWidth={1.75} className="shrink-0" aria-hidden="true" />
            <p className="text-body-sm">{t(language, "chat.errorBody")}</p>
          </div>
          {message.retryText && onRetry && (
            <Button
              size="touch"
              variant="outline"
              className="w-fit gap-2 border-danger-300 text-danger-700 hover:bg-danger-100"
              onClick={() => onRetry(message.retryText!)}
            >
              <RotateCcw size={16} strokeWidth={1.75} />
              {t(language, "chat.tryAgain")}
            </Button>
          )}
        </div>
      </div>
    );
  }

  if (message.card) {
    return (
      <div className="flex justify-start">
        <div className="w-full max-w-[92%]">
          <CardRouter
            card={message.card}
            sessionId={sessionId}
            onSendMessage={onSendMessage}
            onOpenAudit={onOpenAudit}
            sending={sending}
          />
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col gap-1", isUser ? "items-end" : "items-start")}>
      <div
        className={cn(
          "max-w-[85%] px-4 py-3 text-body",
          isUser
            ? cn("rounded-lg rounded-tr-sm", userBubbleClass ?? "bg-structural-600 text-neutral-0")
            : cn("rounded-lg rounded-tl-sm border text-neutral-800", companionBubbleClass ?? "border-neutral-200 bg-neutral-0")
        )}
      >
        <p className="whitespace-pre-wrap">
          {message.text}
          {message.streaming && (
            // ml-0.5: caret sits 2px off the last glyph — optical nudge, not layout spacing
            <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-current align-text-bottom" aria-hidden="true" />
          )}
        </p>
      </div>
      <span className="px-1 text-caption tabular-nums text-neutral-500">{formatTime(message.ts)}</span>
    </div>
  );
}
