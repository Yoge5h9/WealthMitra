import { Link } from "react-router-dom";
import { ArrowUpRight, MessageCircleHeart, Radio, UserRoundCog, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface SurfaceLink {
  to: string;
  label: string;
  description: string;
  icon: LucideIcon;
  /** Wider card for the surface most judges should open first. */
  emphasized?: boolean;
}

export interface SurfaceLinksGridProps {
  spaceId: string | null;
  defaultPersonaId?: string;
  className?: string;
}

/** Links into every surface, each carrying `?space=` so the judge stays in one shared demo space. */
export function SurfaceLinksGrid({ spaceId, defaultPersonaId, className }: SurfaceLinksGridProps) {
  const spaceQuery = spaceId ? `space=${encodeURIComponent(spaceId)}` : "";
  const personaQuery = defaultPersonaId ? `&persona=${encodeURIComponent(defaultPersonaId)}` : "";

  const links: SurfaceLink[] = [
    {
      to: `/app?${spaceQuery}${personaQuery}`,
      label: "Customer app",
      description: "Chat with a persona's companion — net worth, spend, and nudges, all traceable to real data.",
      icon: MessageCircleHeart,
      emphasized: true,
    },
    {
      to: `/rm?${spaceQuery}`,
      label: "RM dashboard",
      description: "The lead queue lighting up the moment chat routes a regulated ask to a human RM.",
      icon: UserRoundCog,
    },
    {
      to: `/channels?${spaceQuery}`,
      label: "Omni-channel",
      description: "Push, SMS, WhatsApp-style, and AI voice-call playback of real AI-generated nudge copy.",
      icon: Radio,
    },
  ];

  return (
    <div className={cn("grid grid-cols-1 gap-4 sm:grid-cols-2", className)}>
      {links.map((link) => (
        <Link
          key={link.label}
          to={link.to}
          className={cn(
            "group flex flex-col justify-between gap-4 rounded-lg border border-neutral-200 bg-neutral-0 p-6 transition-colors duration-[var(--motion-micro)] ease-out hover:border-structural-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]",
            link.emphasized && "sm:col-span-2 sm:flex-row sm:items-center"
          )}
        >
          <div className="flex items-start gap-3">
            <span className="flex size-11 shrink-0 items-center justify-center rounded-md border border-structural-200 bg-structural-50 text-structural-700">
              <link.icon size={20} strokeWidth={1.75} aria-hidden="true" />
            </span>
            <div>
              <p className="font-display text-h4 font-semibold text-neutral-900">{link.label}</p>
              <p className="mt-1 max-w-md text-body-sm text-neutral-600">{link.description}</p>
            </div>
          </div>
          <ArrowUpRight
            size={20}
            strokeWidth={1.75}
            className="shrink-0 self-end text-neutral-400 transition-transform duration-[var(--motion-micro)] ease-out group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-structural-600 sm:self-auto"
            aria-hidden="true"
          />
        </Link>
      ))}
    </div>
  );
}
