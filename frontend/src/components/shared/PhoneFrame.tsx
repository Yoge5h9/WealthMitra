import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { BatteryFull, Bot, CreditCard, Home, MoreHorizontal, SignalHigh, Wallet, Wifi } from "lucide-react";
import { cn } from "@/lib/utils";

export type PhoneFrameNavId = "home" | "pay" | "wealthmitra" | "cards" | "more";

interface NavItem {
  id: PhoneFrameNavId;
  label: string;
  icon: LucideIcon;
}

const NAV_ITEMS: NavItem[] = [
  { id: "home", label: "Home", icon: Home },
  { id: "pay", label: "Pay", icon: Wallet },
  { id: "wealthmitra", label: "WealthMitra", icon: Bot },
  { id: "cards", label: "Cards", icon: CreditCard },
  { id: "more", label: "More", icon: MoreHorizontal },
];

export interface PhoneFrameProps {
  children: ReactNode;
  headerTitle?: string;
  activeNav?: PhoneFrameNavId;
  onNavChange?: (nav: PhoneFrameNavId) => void;
  className?: string;
}

/**
 * The IDBI-mobile-app shell every customer-facing surface renders inside
 * (/app, /present, /channels) — status bar, teal->green header band,
 * five-item bottom nav (WealthMitra center-highlighted), scrollable
 * content viewport.
 */
export function PhoneFrame({
  children,
  headerTitle = "IDBI Bank",
  activeNav = "wealthmitra",
  onNavChange,
  className,
}: PhoneFrameProps) {
  return (
    <div
      className={cn(
        "flex h-[780px] w-[390px] flex-col overflow-hidden rounded-2xl border border-neutral-800 bg-neutral-0 shadow-float-lg",
        className
      )}
    >
      {/* Status bar */}
      <div className="flex shrink-0 items-center justify-between bg-structural-700 px-6 pt-3 pb-1 text-neutral-0">
        <span className="text-caption font-semibold tabular-nums">9:41</span>
        <div className="flex items-center gap-1">
          <SignalHigh size={14} strokeWidth={2} aria-hidden="true" />
          <Wifi size={14} strokeWidth={2} aria-hidden="true" />
          <BatteryFull size={16} strokeWidth={2} aria-hidden="true" />
        </div>
      </div>

      {/* IDBI-style teal->green header band. Kept within structural-700..600
          so white header text clears 4.5:1 across the whole gradient — the
          lighter end of the ramp (400/500) drops white text below 3:1. */}
      <header className="flex shrink-0 items-center justify-between bg-gradient-to-r from-structural-700 to-structural-600 px-4 py-3">
        <span className="font-display text-h4 font-semibold text-neutral-0">{headerTitle}</span>
      </header>

      {/* Scrollable content viewport */}
      <div className="min-h-0 flex-1 overflow-y-auto bg-neutral-50">{children}</div>

      {/* Bottom nav */}
      <nav
        className="flex shrink-0 items-stretch justify-around border-t border-neutral-200 bg-neutral-0 px-1 pt-1 pb-2"
        aria-label="Primary"
      >
        {NAV_ITEMS.map((item) => {
          const isActive = item.id === activeNav;
          const isCenter = item.id === "wealthmitra";
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onNavChange?.(item.id)}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "flex min-h-11 min-w-11 flex-1 flex-col items-center justify-center gap-1 rounded-sm py-1 text-caption transition-colors duration-[var(--motion-micro)] ease-out focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]",
                isCenter
                  ? "text-brand-700"
                  : isActive
                    ? "text-structural-600"
                    : "text-neutral-500 hover:text-neutral-700"
              )}
            >
              <span
                className={cn(
                  "flex size-8 items-center justify-center rounded-full",
                  isCenter && "-mt-4 bg-brand-500 text-neutral-950 shadow-float-md"
                )}
              >
                <item.icon size={isCenter ? 20 : 20} strokeWidth={1.75} aria-hidden="true" />
              </span>
              <span className={cn("font-medium", isCenter && "text-brand-700")}>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}
