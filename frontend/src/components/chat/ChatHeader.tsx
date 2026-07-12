import { useLayoutEffect, useMemo, useRef, useState, type ReactNode, type RefObject } from "react";
import { motion } from "framer-motion";
import { LayoutDashboard, MessageCircle, Volume2, VolumeX } from "lucide-react";
import { Tooltip } from "radix-ui";
import { Avatar } from "@/components/shared/Avatar";
import { LanguageDropdown } from "@/components/chat/LanguageDropdown";
import type { LanguageCode } from "@/components/shared/LangToggle";
import { cn } from "@/lib/utils";
import { t, type TKey } from "@/lib/i18n";
import type { AvatarState } from "@/lib/types";

export type AppTab = "chat" | "dashboard";

const TOUR_SEEN_KEY = "wm_header_tour_seen";

const AVATAR_STATUS_KEY: Record<AvatarState, TKey> = {
  idle: "header.status.idle",
  listening: "header.status.listening",
  thinking: "header.status.thinking",
  speaking: "header.status.speaking",
  celebrating: "header.status.celebrating",
  concerned: "header.status.concerned",
};

const AVATAR_DOT_CLASS: Record<AvatarState, string> = {
  idle: "bg-neutral-300",
  listening: "bg-structural-500 animate-pulse",
  thinking: "bg-structural-500 animate-pulse",
  speaking: "bg-structural-500 animate-pulse",
  celebrating: "bg-success-500",
  concerned: "bg-warning-500",
};

export interface ChatHeaderProps {
  personaName: string;
  avatarState: AvatarState;
  language: LanguageCode;
  onLanguageChange: (lang: LanguageCode) => void;
  speechSupported: boolean;
  speechEnabled: boolean;
  onToggleSpeech: () => void;
  onSwitchPersona: () => void;
  tab: AppTab;
  onTabChange: (tab: AppTab) => void;
  /** Auto-launch the first-run icon coachmark. Off in the embedded presenter
   * stage (/present), where an overlay would cover the greeting and the stage
   * already carries its own guided walkthrough. */
  autoTour?: boolean;
}

function IconTooltip({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <Tooltip.Root>
      <Tooltip.Trigger asChild>{children}</Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content
          side="bottom"
          sideOffset={6}
          className="z-50 max-w-56 rounded-sm border border-neutral-200 bg-neutral-0 px-3 py-2 text-caption text-neutral-700 shadow-float-md"
        >
          {label}
          <Tooltip.Arrow className="fill-neutral-0" />
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}

interface TourStep {
  id: string;
  ref: RefObject<HTMLElement | null>;
  titleKey: TKey;
  bodyKey: TKey;
}

/**
 * Compact, unified chat header: one tight row for presence + persona-switch
 * + language/voice, and a slim icon-labelled Chat/Dashboard toggle merged
 * directly beneath it. The audit trail lives outside the phone now
 * (JudgePanel) — it's an evaluator affordance, not something a real bank
 * customer sees in-app.
 */
export function ChatHeader({
  personaName,
  avatarState,
  language,
  onLanguageChange,
  speechSupported,
  speechEnabled,
  onToggleSpeech,
  onSwitchPersona,
  tab,
  onTabChange,
  autoTour = true,
}: ChatHeaderProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const languageWrapRef = useRef<HTMLDivElement>(null);
  const voiceWrapRef = useRef<HTMLDivElement>(null);
  const dashboardTabRef = useRef<HTMLButtonElement>(null);

  const steps: TourStep[] = useMemo(() => {
    const arr: TourStep[] = [
      { id: "language", ref: languageWrapRef, titleKey: "tour.language.title", bodyKey: "tour.language.body" },
    ];
    if (speechSupported) {
      arr.push({ id: "voice", ref: voiceWrapRef, titleKey: "tour.voice.title", bodyKey: "tour.voice.body" });
    }
    arr.push({ id: "dashboardTab", ref: dashboardTabRef, titleKey: "tour.dashboardTab.title", bodyKey: "tour.dashboardTab.body" });
    return arr;
    // speechSupported is feature-detected once and doesn't change mid-session.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [speechSupported]);

  const [tourStep, setTourStep] = useState<number | null>(() => {
    if (!autoTour) return null;
    try {
      return window.sessionStorage.getItem(TOUR_SEEN_KEY) ? null : 0;
    } catch {
      return null;
    }
  });
  const [tourPos, setTourPos] = useState<{ top: number; left: number } | null>(null);

  useLayoutEffect(() => {
    if (tourStep === null) {
      setTourPos(null);
      return;
    }
    const step = steps[tourStep];
    const containerEl = containerRef.current;
    const targetEl = step?.ref.current;
    if (!containerEl || !targetEl) {
      setTourPos(null);
      return;
    }
    const cRect = containerEl.getBoundingClientRect();
    const tRect = targetEl.getBoundingClientRect();
    const cardWidth = 232;
    const rawLeft = tRect.left - cRect.left + tRect.width / 2 - cardWidth / 2;
    const left = Math.min(Math.max(rawLeft, 8), Math.max(cRect.width - cardWidth - 8, 8));
    setTourPos({ top: tRect.bottom - cRect.top + 8, left });
  }, [tourStep, steps]);

  function finishTour() {
    try {
      window.sessionStorage.setItem(TOUR_SEEN_KEY, "1");
    } catch {
      // sessionStorage unavailable — the tour just won't remember dismissal, not fatal.
    }
    setTourStep(null);
  }

  function advanceTour() {
    setTourStep((current) => {
      if (current === null) return null;
      if (current + 1 >= steps.length) {
        finishTour();
        return null;
      }
      return current + 1;
    });
  }

  const activeStepId = tourStep !== null ? steps[tourStep]?.id : null;
  const ringClass = "ring-2 ring-brand-400 ring-offset-2 ring-offset-neutral-0 rounded-full";

  return (
    <Tooltip.Provider delayDuration={300}>
      <div ref={containerRef} className="relative shrink-0 border-b border-neutral-200 bg-neutral-0">
        {/* Row 1: presence + persona switch + language/voice/audit */}
        <div className="flex items-center gap-2.5 px-4 py-2">
          <IconTooltip label={t(language, "header.tooltip.switchPersona")}>
            <button
              type="button"
              onClick={onSwitchPersona}
              aria-label={t(language, "header.tooltip.switchPersona")}
              className="relative shrink-0 rounded-full focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
            >
              <Avatar state={avatarState} size={32} />
              <span
                aria-hidden="true"
                className={cn(
                  "absolute bottom-0 right-0 size-2.5 rounded-full border-2 border-neutral-0",
                  AVATAR_DOT_CLASS[avatarState]
                )}
              />
            </button>
          </IconTooltip>

          <div className="min-w-0 flex-1">
            <p className="truncate text-body-sm font-semibold leading-tight text-neutral-900">{personaName}</p>
            <p className="truncate text-caption leading-tight text-neutral-500">{t(language, AVATAR_STATUS_KEY[avatarState])}</p>
          </div>

          <div ref={languageWrapRef} className={cn(activeStepId === "language" && ringClass)}>
            <IconTooltip label={t(language, "header.tooltip.language")}>
              <div>
                <LanguageDropdown value={language} onChange={onLanguageChange} />
              </div>
            </IconTooltip>
          </div>

          {speechSupported && (
            <div ref={voiceWrapRef} className={cn(activeStepId === "voice" && ringClass)}>
              <IconTooltip label={t(language, speechEnabled ? "header.tooltip.voiceOn" : "header.tooltip.voiceOff")}>
                <button
                  type="button"
                  aria-label={t(language, speechEnabled ? "header.tooltip.voiceOn" : "header.tooltip.voiceOff")}
                  aria-pressed={speechEnabled}
                  onClick={onToggleSpeech}
                  className="flex size-9 shrink-0 items-center justify-center rounded-full text-neutral-500 transition-colors duration-[var(--motion-micro)] ease-out hover:text-structural-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
                >
                  {speechEnabled ? <Volume2 size={19} strokeWidth={1.75} /> : <VolumeX size={19} strokeWidth={1.75} />}
                </button>
              </IconTooltip>
            </div>
          )}
        </div>

        {/* Row 2: Chat/Dashboard, merged directly under row 1 — no separate border/gutter */}
        <div className="flex gap-1 px-3 pb-2" role="tablist">
          <IconTooltip label={t(language, "header.tooltip.chatTab")}>
            <button
              type="button"
              role="tab"
              aria-selected={tab === "chat"}
              onClick={() => onTabChange("chat")}
              className={cn(
                "flex min-h-11 flex-1 items-center justify-center gap-1.5 rounded-full text-body-sm font-medium transition-colors duration-[var(--motion-micro)] ease-out focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]",
                tab === "chat" ? "bg-structural-50 text-structural-700" : "text-neutral-500 hover:text-neutral-700"
              )}
            >
              <MessageCircle size={16} strokeWidth={1.75} aria-hidden="true" />
              {t(language, "header.tab.chat")}
            </button>
          </IconTooltip>
          <IconTooltip label={t(language, "header.tooltip.dashboardTab")}>
            <button
              ref={dashboardTabRef}
              type="button"
              role="tab"
              aria-selected={tab === "dashboard"}
              onClick={() => onTabChange("dashboard")}
              className={cn(
                "flex min-h-11 flex-1 items-center justify-center gap-1.5 rounded-full text-body-sm font-medium transition-colors duration-[var(--motion-micro)] ease-out focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]",
                activeStepId === "dashboardTab" && ringClass,
                tab === "dashboard" ? "bg-structural-50 text-structural-700" : "text-neutral-500 hover:text-neutral-700"
              )}
            >
              <LayoutDashboard size={16} strokeWidth={1.75} aria-hidden="true" />
              {t(language, "header.tab.dashboard")}
            </button>
          </IconTooltip>
        </div>

        {tourStep !== null && tourPos && steps[tourStep] && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
            style={{ top: tourPos.top, left: tourPos.left, width: 232 }}
            className="absolute z-30 rounded-lg border border-structural-200 bg-neutral-0 p-3 shadow-float-lg"
            role="dialog"
            aria-label={t(language, steps[tourStep].titleKey)}
          >
            <p className="text-body-sm font-semibold text-structural-700">{t(language, steps[tourStep].titleKey)}</p>
            <p className="mt-1 text-caption text-neutral-600">{t(language, steps[tourStep].bodyKey)}</p>
            <div className="mt-2.5 flex items-center justify-between">
              <span className="text-caption text-neutral-400">
                {t(language, "tour.step", { current: tourStep + 1, total: steps.length })}
              </span>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={finishTour}
                  className="text-caption font-medium text-neutral-500 hover:text-neutral-700"
                >
                  {t(language, "tour.skip")}
                </button>
                <button
                  type="button"
                  onClick={advanceTour}
                  className="rounded-full bg-structural-600 px-3 py-1.5 text-caption font-medium text-neutral-0 hover:bg-structural-700"
                >
                  {tourStep === steps.length - 1 ? t(language, "tour.done") : t(language, "tour.next")}
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </Tooltip.Provider>
  );
}
