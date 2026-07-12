import { ScrollText, Volume2, VolumeX } from "lucide-react";
import { Avatar } from "@/components/shared/Avatar";
import { LangToggle, type LanguageCode } from "@/components/shared/LangToggle";
import type { AvatarState } from "@/lib/types";

export interface ChatHeaderProps {
  personaName: string;
  avatarState: AvatarState;
  language: LanguageCode;
  onLanguageChange: (lang: LanguageCode) => void;
  speechSupported: boolean;
  speechEnabled: boolean;
  onToggleSpeech: () => void;
  onOpenAudit: () => void;
}

const AVATAR_STATUS_LABEL: Record<AvatarState, string> = {
  idle: "Here to help",
  listening: "Listening…",
  thinking: "Thinking…",
  speaking: "Replying…",
  celebrating: "Nice work!",
  concerned: "Here for you",
};

/** Sticky in-chat header: live companion presence + language + voice-out +
 * the audit-drawer entry point (the trust cue). */
export function ChatHeader({
  personaName,
  avatarState,
  language,
  onLanguageChange,
  speechSupported,
  speechEnabled,
  onToggleSpeech,
  onOpenAudit,
}: ChatHeaderProps) {
  return (
    <div className="sticky top-0 z-10 flex items-center gap-3 border-b border-neutral-200 bg-neutral-0 px-4 py-3">
      <Avatar state={avatarState} size={36} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-body-sm font-semibold text-neutral-900">WealthMitra</p>
        <p className="truncate text-caption text-neutral-500">
          {AVATAR_STATUS_LABEL[avatarState]} · for {personaName}
        </p>
      </div>

      <LangToggle value={language} onChange={onLanguageChange} />

      {speechSupported && (
        <button
          type="button"
          aria-label={speechEnabled ? "Turn off spoken replies" : "Turn on spoken replies"}
          aria-pressed={speechEnabled}
          onClick={onToggleSpeech}
          className="flex size-11 shrink-0 items-center justify-center rounded-full text-neutral-500 transition-colors duration-[var(--motion-micro)] ease-out hover:text-structural-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
        >
          {speechEnabled ? <Volume2 size={20} strokeWidth={1.75} /> : <VolumeX size={20} strokeWidth={1.75} />}
        </button>
      )}

      <button
        type="button"
        aria-label="Why this number — view the audit trail"
        onClick={onOpenAudit}
        className="flex size-11 shrink-0 items-center justify-center rounded-full text-neutral-500 transition-colors duration-[var(--motion-micro)] ease-out hover:text-structural-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
      >
        <ScrollText size={20} strokeWidth={1.75} />
      </button>
    </div>
  );
}
