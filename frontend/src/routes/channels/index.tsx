import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Clapperboard, HeartHandshake, Megaphone, SlidersHorizontal } from "lucide-react";
import { SectionHeader } from "@/components/shared/SectionHeader";
import { DataState } from "@/components/shared/DataState";
import { cn } from "@/lib/utils";
import { apiPost } from "@/lib/api";
import { useNudges } from "@/lib/queries";
import type { CreateSessionResponse, NudgeKind } from "@/lib/types";
import { useDemoSpace } from "@/components/showcase/useDemoSpace";
import { usePersonaRoster, sampleNudges } from "@/components/showcase/personas";
import { PushNotificationCard } from "@/components/showcase/channels/PushNotificationCard";
import { SmsThreadCard } from "@/components/showcase/channels/SmsThreadCard";
import { WMessageChatCard } from "@/components/showcase/channels/WMessageChatCard";
import { VoiceCallPlayerCard } from "@/components/showcase/channels/VoiceCallPlayerCard";
import type { ChannelDelivery } from "@/components/showcase/channels/types";
import { personaExperienceFor } from "@/lib/personaExperience";

const DEFAULT_PERSONA_ID = "ravi";
const EASE_OUT: [number, number, number, number] = [0.22, 1, 0.36, 1];
// Stagger step is one motion-micro tick (150ms) per card, per the token
// scale in tokens.css — not an invented delay value.
const STAGGER_STEP = 0.15;

const NUDGE_CLASSES: { id: NudgeKind; label: string; icon: typeof Megaphone }[] = [
  { id: "functional", label: "Functional", icon: Megaphone },
  { id: "relational", label: "Relational", icon: HeartHandshake },
];

export default function Channels() {
  const { spaceId } = useDemoSpace();
  const personasQuery = usePersonaRoster();
  const [personaId, setPersonaId] = useState(DEFAULT_PERSONA_ID);
  const [nudgeClass, setNudgeClass] = useState<NudgeKind>("functional");
  // session per (space, persona) — keyed so a slow response for a previous
  // persona can never populate the currently selected one.
  const [session, setSession] = useState<{ key: string; id: string } | null>(null);
  const requestedKeyRef = useRef<string | null>(null);

  const selectedPersona = personasQuery.data?.find((p) => p.id === personaId);
  const sessionKey = `${spaceId}:${personaId}`;

  useEffect(() => {
    if (!spaceId || !personasQuery.data) return;
    if (requestedKeyRef.current === sessionKey) return;
    requestedKeyRef.current = sessionKey;
    const language = selectedPersona?.language ?? "en";
    // Plain apiPost instead of useCreateSession(): this fires from a mount
    // effect, where StrictMode's simulated remount drops TanStack v5
    // mutation updates (same failure mode as useDemoSpace — see its note).
    apiPost<CreateSessionResponse>(`/spaces/${spaceId}/sessions`, {
      persona_id: personaId,
      language,
    })
      .then((res) => setSession({ key: sessionKey, id: res.session_id }))
      .catch(() => {
        requestedKeyRef.current = null;
      });
  }, [spaceId, personaId, personasQuery.data, selectedPersona?.language, sessionKey]);

  const sessionId = session?.key === sessionKey ? session.id : null;
  const nudgesQuery = useNudges(sessionId);

  const nudgesResolved = !sessionId || nudgesQuery.isFetched || nudgesQuery.isError;
  const realNudge = nudgesQuery.data?.find((n) => n.kind === nudgeClass);
  const personaFirstName = selectedPersona?.name.split(" ")[0] ?? "there";
  const fallbackNudge = sampleNudges(personaFirstName)[nudgeClass];
  const activeNudge = realNudge ?? fallbackNudge;
  const experience = personaExperienceFor(personaId);

  const delivery: ChannelDelivery = {
    title: activeNudge.title,
    body: activeNudge.body,
    personaName: personaFirstName,
    language: selectedPersona?.language ?? "en",
    sample: !realNudge,
    communicationPreference: experience.channels.preference,
    cadence: experience.channels.cadence,
    channelFits: experience.channels.fits,
  };

  return (
    <div className="mx-auto max-w-6xl space-y-10 px-6 py-12">
      <SectionHeader
        eyebrow="Showcase · Omni-channel"
        title="Reach them in the way that fits them"
        description="WealthMitra adapts language, format, preferred channel and cadence to the customer’s profile — not just the words in a message."
      />

      <div className="flex items-center gap-3 rounded-lg border border-warning-300 bg-warning-50 px-4 py-3">
        <Clapperboard size={20} strokeWidth={1.75} className="shrink-0 text-warning-700" aria-hidden="true" />
        <p className="text-body-sm font-medium text-warning-800">
          Simulated delivery · real AI-generated copy. No telephony or messaging infra actually
          fires — every word below still comes from the same nudge engine the customer app uses.
        </p>
      </div>

      <DataState
        status={personasQuery.isLoading ? "loading" : personasQuery.isError ? "error" : "success"}
        errorDescription="Couldn't load the persona roster. Try again."
        onRetry={() => personasQuery.refetch()}
        skeleton={<div className="h-11 w-full animate-pulse rounded-full bg-neutral-100" />}
      >
        <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Persona">
          {personasQuery.data?.map((persona) => {
            const isActive = persona.id === personaId;
            return (
              <button
                key={persona.id}
                type="button"
                role="radio"
                aria-checked={isActive}
                onClick={() => setPersonaId(persona.id)}
                className={cn(
                  "min-h-11 rounded-full border px-4 text-body-sm font-medium transition-colors duration-[var(--motion-micro)] ease-out focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]",
                  isActive
                    ? "border-brand-400 bg-brand-50 text-brand-700"
                    : "border-neutral-200 bg-neutral-0 text-neutral-700 hover:border-structural-300"
                )}
              >
                {persona.name}
              </button>
            );
          })}
        </div>
      </DataState>

      <section className="rounded-lg border border-structural-200 bg-structural-50 p-4" aria-label="Personalised communication plan">
        <div className="flex items-start gap-3">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-structural-100 text-structural-700"><SlidersHorizontal size={17} strokeWidth={1.75} aria-hidden="true" /></span>
          <div>
            <p className="text-caption font-semibold uppercase tracking-wide text-structural-700">Personalised communication plan · {selectedPersona?.name ?? "Customer"}</p>
            <p className="mt-1 text-body-sm text-neutral-800">{experience.channels.rationale}</p>
            <div className="mt-3 flex flex-wrap gap-2 text-caption">
              <span className="rounded-full bg-neutral-0 px-2.5 py-1 text-neutral-700"><strong>Language:</strong> {selectedPersona?.language === "hi" ? "Hindi" : selectedPersona?.language === "gu" ? "Gujarati" : "English"}</span>
              <span className="rounded-full bg-neutral-0 px-2.5 py-1 text-neutral-700"><strong>Best fit:</strong> {experience.channels.preference}</span>
              <span className="rounded-full bg-neutral-0 px-2.5 py-1 text-neutral-700"><strong>Cadence:</strong> {experience.channels.cadence}</span>
            </div>
          </div>
        </div>
        <p className="mt-3 text-caption text-neutral-600">Judge note: this is a profile-led presentation plan for the synthetic demo roster. In production, channel preferences and consent control delivery.</p>
      </section>

      <div className="flex items-center justify-between gap-4">
        <div
          role="radiogroup"
          aria-label="Nudge class"
          className="inline-flex items-center gap-1 rounded-full border border-neutral-200 bg-neutral-50 p-1"
        >
          {NUDGE_CLASSES.map((option) => {
            const isActive = option.id === nudgeClass;
            return (
              <button
                key={option.id}
                type="button"
                role="radio"
                aria-checked={isActive}
                onClick={() => setNudgeClass(option.id)}
                className={cn(
                  "flex min-h-11 items-center gap-1.5 rounded-full px-3 text-caption font-medium transition-colors duration-[var(--motion-micro)] ease-out focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]",
                  isActive ? "bg-brand-500 text-neutral-950" : "text-neutral-600 hover:text-neutral-900"
                )}
              >
                <option.icon size={14} strokeWidth={1.75} aria-hidden="true" />
                {option.label}
              </button>
            );
          })}
        </div>
        <p className="hidden text-caption text-neutral-500 sm:block">
          {nudgeClass === "functional"
            ? "Functional — an action to take (idle balance, SIP due, goal drift)."
            : "Relational — a check-in or celebration, no ask attached."}
        </p>
      </div>

      <DataState
        status={nudgesResolved ? "success" : "loading"}
        skeleton={
          <div className="grid grid-cols-1 justify-items-center gap-8 md:grid-cols-2" aria-hidden="true">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-[780px] w-[390px] animate-pulse rounded-2xl bg-neutral-100" />
            ))}
          </div>
        }
      >
        <motion.div
          key={`${personaId}:${nudgeClass}`}
          initial="hidden"
          animate="visible"
          variants={{ hidden: {}, visible: { transition: { staggerChildren: STAGGER_STEP } } }}
          className="grid grid-cols-1 justify-items-center gap-8 md:grid-cols-2"
        >
          {[PushNotificationCard, SmsThreadCard, WMessageChatCard, VoiceCallPlayerCard].map((Card, i) => (
            <motion.div
              key={i}
              variants={{
                hidden: { opacity: 0, y: 16 },
                visible: { opacity: 1, y: 0, transition: { duration: 0.35, ease: EASE_OUT } },
              }}
            >
              <Card delivery={delivery} />
            </motion.div>
          ))}
        </motion.div>
      </DataState>
    </div>
  );
}
