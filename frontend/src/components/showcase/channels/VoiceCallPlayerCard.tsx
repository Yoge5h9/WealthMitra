import { useEffect, useMemo, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Pause, Phone, Play, VolumeX } from "lucide-react";
import { PhoneFrame } from "@/components/shared/PhoneFrame";
import { Avatar } from "@/components/shared/Avatar";
import { Button } from "@/components/ui/button";
import { SampleTag } from "@/components/showcase/channels/SampleTag";
import type { ChannelDelivery } from "@/components/showcase/channels/types";

const SPEECH_LANG: Record<string, string> = { en: "en-IN", hi: "hi-IN", gu: "gu-IN" };
const BAR_COUNT = 18;

function supportsSpeech(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

/** AI voice-call player — waveform + browser `speechSynthesis` reading the nudge copy aloud. */
export function VoiceCallPlayerCard({ delivery }: { delivery: ChannelDelivery }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [supported] = useState(supportsSpeech);
  const reduceMotion = Boolean(useReducedMotion());
  const barHeights = useMemo(
    () => Array.from({ length: BAR_COUNT }, (_, i) => 6 + ((i * 7) % 20)),
    []
  );

  useEffect(() => {
    return () => {
      if (supported) window.speechSynthesis.cancel();
    };
  }, [supported]);

  useEffect(() => {
    if (!supported) return;
    setIsPlaying(false);
    window.speechSynthesis.cancel();
    // Stopping playback whenever the underlying delivery changes (persona
    // switch, nudge-class toggle) — a stale utterance must never keep
    // reading copy that's no longer on screen.
  }, [delivery.title, delivery.body, supported]);

  function toggle() {
    if (!supported) return;
    if (isPlaying) {
      window.speechSynthesis.cancel();
      setIsPlaying(false);
      return;
    }
    const utterance = new SpeechSynthesisUtterance(`${delivery.title}. ${delivery.body}`);
    utterance.lang = SPEECH_LANG[delivery.language] ?? "en-IN";
    utterance.onend = () => setIsPlaying(false);
    utterance.onerror = () => setIsPlaying(false);
    window.speechSynthesis.speak(utterance);
    setIsPlaying(true);
  }

  return (
    <PhoneFrame headerTitle="Voice call">
      <div className="flex h-full flex-col items-center justify-between bg-structural-900 px-6 py-8 text-neutral-0">
        <div className="flex flex-col items-center gap-3">
          <span className="text-caption font-medium uppercase tracking-wide text-structural-300">
            WealthMitra Voice · Incoming
          </span>
          <Avatar state={isPlaying ? "speaking" : "idle"} size={88} />
          <p className="font-display text-h4 font-semibold">{delivery.personaName}'s companion</p>
          {delivery.sample && <SampleTag />}
        </div>

        <div className="flex h-16 w-full items-end justify-center gap-1" aria-hidden="true">
          {barHeights.map((height, index) => (
            <motion.span
              key={index}
              className="w-1.5 rounded-full bg-structural-400"
              style={{ height }}
              animate={
                isPlaying && !reduceMotion
                  ? { scaleY: [0.4, 1, 0.5, 0.9, 0.4] }
                  : { scaleY: 0.3 }
              }
              transition={
                isPlaying && !reduceMotion
                  ? { duration: 0.9, repeat: Infinity, ease: "easeInOut", delay: index * 0.04 }
                  : { duration: 0.2 }
              }
            />
          ))}
        </div>

        <div className="flex w-full flex-col items-center gap-3">
          {supported ? (
            <Button
              size="icon-touch"
              onClick={toggle}
              aria-label={isPlaying ? "Pause voice playback" : "Play voice playback"}
              className="size-14 rounded-full bg-brand-500 text-neutral-950 hover:bg-brand-400"
            >
              {isPlaying ? (
                <Pause size={24} strokeWidth={2} aria-hidden="true" />
              ) : (
                <Play size={24} strokeWidth={2} className="ml-0.5" aria-hidden="true" />
              )}
            </Button>
          ) : (
            <div className="flex items-center gap-2 rounded-md border border-structural-700 bg-structural-800 px-3 py-2 text-caption text-structural-200">
              <VolumeX size={16} strokeWidth={1.75} aria-hidden="true" />
              Voice playback isn't supported in this browser
            </div>
          )}
          <p className="flex items-center gap-1.5 text-caption text-structural-300">
            <Phone size={13} strokeWidth={1.75} aria-hidden="true" />
            Simulated call · real AI-generated copy, read aloud
          </p>
        </div>
      </div>
    </PhoneFrame>
  );
}
