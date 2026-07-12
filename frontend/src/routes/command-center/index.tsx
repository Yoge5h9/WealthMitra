import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DataState } from "@/components/shared/DataState";
import { SectionHeader } from "@/components/shared/SectionHeader";
import { useDemoSpace } from "@/components/showcase/useDemoSpace";
import { usePersonaRoster } from "@/components/showcase/personas";
import { PersonaCard } from "@/components/showcase/PersonaCard";
import { SurfaceLinksGrid } from "@/components/showcase/SurfaceLinksGrid";
import { DisclosureTable } from "@/components/showcase/DisclosureTable";
import { GuidedTour } from "@/components/showcase/GuidedTour";
import { ResetDemoButton } from "@/components/showcase/ResetDemoButton";

const DEFAULT_PERSONA_ID = "ravi";

function scrollToPersonas(target: HTMLElement | null) {
  if (!target) return;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  target.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
}

export default function CommandCenter() {
  const { spaceId } = useDemoSpace();
  const navigate = useNavigate();
  const personasQuery = usePersonaRoster();
  const [selectedPersonaId, setSelectedPersonaId] = useState(DEFAULT_PERSONA_ID);
  const [tourReplaySignal, setTourReplaySignal] = useState(0);
  const personaSectionRef = useRef<HTMLDivElement>(null);

  function handleSelectPersona(personaId: string) {
    setSelectedPersonaId(personaId);
    const params = new URLSearchParams();
    if (spaceId) params.set("space", spaceId);
    params.set("persona", personaId);
    navigate(`/app?${params.toString()}`);
  }

  return (
    <div className="mx-auto max-w-6xl space-y-16 px-6 py-12">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-2xl border border-structural-800 bg-gradient-to-br from-structural-900 via-structural-800 to-structural-600 px-6 py-16 sm:px-12 sm:py-20">
        <div className="flex max-w-2xl flex-col items-start gap-6">
          <span className="inline-flex items-center gap-2 rounded-full border border-neutral-0/25 bg-neutral-0/10 px-3 py-1 text-caption font-semibold uppercase tracking-wide text-structural-100">
            <Sparkles size={14} strokeWidth={1.75} aria-hidden="true" />
            IDBI Innovate 2026 · Track 01 prototype
          </span>
          <h1 className="font-display text-display font-bold tracking-tight text-neutral-0">
            A wealth companion that's on your side.
          </h1>
          <p className="max-w-xl text-lg text-structural-50">
            WealthMitra turns fragmented bank and Account Aggregator data into a conversational
            companion that explains your money honestly — and knows exactly when to hand you off
            to a human. This is a real working advisory engine, with each customer's data already
            loaded. Here's what to try.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Button
              size="touch"
              className="gap-2"
              onClick={() => scrollToPersonas(personaSectionRef.current)}
            >
              Start the demo
              <ArrowRight size={18} strokeWidth={2} aria-hidden="true" />
            </Button>
            <Button
              size="touch"
              variant="outline"
              className="border-neutral-0/30 bg-transparent text-neutral-0 hover:bg-neutral-0/10 hover:text-neutral-0"
              onClick={() => setTourReplaySignal((n) => n + 1)}
            >
              Replay guided tour
            </Button>
          </div>
        </div>
      </section>

      {/* Persona switcher */}
      <section ref={personaSectionRef} className="scroll-mt-8 space-y-6">
        <SectionHeader
          eyebrow="Step 1 · Pick a persona"
          title="Seven different money stories"
          description="Each persona carries its own real bank transactions, goals, and (where noted) Account Aggregator holdings. Picking one deep-links straight into a live chat with their companion."
        />
        <DataState
          status={personasQuery.isLoading ? "loading" : personasQuery.isError ? "error" : personasQuery.data?.length ? "success" : "empty"}
          emptyTitle="No personas seeded yet"
          emptyDescription="The persona roster couldn't be found on this backend."
          errorDescription="Couldn't load the persona roster. Your demo space is still safe — try again."
          onRetry={() => personasQuery.refetch()}
          skeleton={
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-hidden="true">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="h-44 animate-pulse rounded-lg border border-neutral-200 bg-neutral-100" />
              ))}
            </div>
          }
        >
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {personasQuery.data?.map((persona) => (
              <PersonaCard
                key={persona.id}
                persona={persona}
                selected={persona.id === selectedPersonaId}
                onSelect={handleSelectPersona}
              />
            ))}
          </div>
        </DataState>
      </section>

      {/* Surface links */}
      <section className="space-y-6">
        <SectionHeader
          eyebrow="Step 2 · Explore every surface"
          title="One engine, four ways to see it"
          description="Every link below shares this same demo space — actions on one surface show up live on the others."
        />
        <SurfaceLinksGrid spaceId={spaceId} defaultPersonaId={selectedPersonaId} />
      </section>

      {/* Honest disclosure */}
      <DisclosureTable />

      {/* Space utilities */}
      <section className="flex flex-col gap-3 border-t border-neutral-200 pt-8 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-caption text-neutral-500">
          Demo space:{" "}
          <span className="font-medium tabular-nums text-neutral-700">{spaceId ?? "provisioning…"}</span>
        </p>
        <ResetDemoButton spaceId={spaceId} />
      </section>

      <GuidedTour reopenSignal={tourReplaySignal} />
    </div>
  );
}
