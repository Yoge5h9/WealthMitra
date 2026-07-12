import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  BellRing,
  BookOpen,
  Info,
  PartyPopper,
  ShieldAlert,
  Sparkles,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";
import { DataState } from "@/components/shared/DataState";
import { useNudges } from "@/lib/queries";
import { useSpaceSocket } from "@/hooks/useSpaceSocket";
import type { Nudge, NudgeIntent } from "@/lib/types";

export interface NudgeFeedProps {
  sessionId: string;
  spaceId: string | null;
  personaId: string;
}

const INTENT_ICON: Record<NudgeIntent, LucideIcon> = {
  motivational: TrendingUp,
  protective: ShieldAlert,
  opportunity: Sparkles,
  contextual: Info,
  literacy: BookOpen,
  celebration: PartyPopper,
};

/**
 * `kind` distinguishes functional (system/task-driven) from relational
 * (companion check-in) nudges — visually distinct via icon container +
 * label, never color alone, so it reads for color-blind users too.
 */
function NudgeRow({ nudge }: { nudge: Nudge }) {
  const Icon = INTENT_ICON[nudge.intent] ?? Info;
  const isFunctional = nudge.kind === "functional";
  return (
    <motion.li
      layout
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
      className="rounded-lg border border-neutral-200 p-3"
    >
      <div className="flex items-start gap-2.5">
        <span
          className={
            "flex size-8 shrink-0 items-center justify-center rounded-full " +
            (isFunctional ? "bg-structural-50 text-structural-600" : "bg-neutral-100 text-neutral-700")
          }
        >
          <Icon size={15} strokeWidth={1.75} aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="truncate text-body-sm font-medium text-neutral-900">{nudge.title}</p>
            <span
              className={
                "shrink-0 rounded-xs px-1.5 py-0.5 text-caption font-semibold uppercase tracking-wide " +
                (isFunctional ? "bg-structural-50 text-structural-700" : "bg-neutral-100 text-neutral-600")
              }
            >
              {isFunctional ? "Nudge" : "Check-in"}
            </span>
          </div>
          <p className="mt-1 text-caption text-neutral-600">{nudge.body}</p>
        </div>
      </div>
    </motion.li>
  );
}

/** Live nudge feed: seeds from the day's cached feed, then splices in any
 * `nudge.created` WS event for this persona as it arrives (Task 13's event,
 * already wired into chat — this surface just also listens for it). */
export function NudgeFeed({ sessionId, spaceId, personaId }: NudgeFeedProps) {
  const query = useNudges(sessionId);
  const { subscribe } = useSpaceSocket(spaceId);
  const [live, setLive] = useState<Nudge[]>([]);

  useEffect(() => {
    return subscribe("nudge.created", (nudge) => {
      if (nudge.persona_id !== personaId) return;
      setLive((prev) => (prev.some((n) => n.id === nudge.id) ? prev : [nudge, ...prev]));
    });
  }, [subscribe, personaId]);

  const known = new Set((query.data ?? []).map((n) => n.id));
  const merged = [...live.filter((n) => !known.has(n.id)), ...(query.data ?? [])];

  return (
    <DataState
      status={query.isLoading ? "loading" : query.isError ? "error" : merged.length === 0 ? "empty" : "success"}
      onRetry={() => query.refetch()}
      emptyIcon={BellRing}
      emptyTitle="No nudges today"
      emptyDescription="WealthMitra checks in when something worth acting on shows up in your data."
    >
      <ul className="space-y-2">
        {merged.map((nudge) => (
          <NudgeRow key={nudge.id} nudge={nudge} />
        ))}
      </ul>
    </DataState>
  );
}
