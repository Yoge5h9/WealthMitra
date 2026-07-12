/**
 * Optional voice, graceful everywhere: Web Speech API mic input (feature-
 * detected `SpeechRecognition`/`webkitSpeechRecognition`) and speech
 * synthesis output (feature-detected `window.speechSynthesis`). Neither
 * API has TS lib.dom coverage for the non-standard recognition constructor,
 * so it's typed narrowly here rather than reaching for a blanket `any`.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import type { LanguageCode } from "@/components/shared/LangToggle";

interface SpeechRecognitionResultLike {
  transcript: string;
}

interface SpeechRecognitionEventLike {
  results: ArrayLike<ArrayLike<SpeechRecognitionResultLike>>;
}

interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

function getSpeechRecognitionCtor(): SpeechRecognitionConstructor | null {
  const w = window as unknown as {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

const RECOGNITION_LANG: Record<LanguageCode, string> = { en: "en-IN", hi: "hi-IN", gu: "gu-IN" };

export interface UseVoiceInputResult {
  supported: boolean;
  listening: boolean;
  toggle: () => void;
}

/** Mic button state machine. Hidden entirely by the caller when `!supported`. */
export function useVoiceInput(language: LanguageCode, onResult: (text: string) => void): UseVoiceInputResult {
  const ctorRef = useRef<SpeechRecognitionConstructor | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const onResultRef = useRef(onResult);
  onResultRef.current = onResult;
  const [listening, setListening] = useState(false);
  const [supported, setSupported] = useState(false);

  useEffect(() => {
    ctorRef.current = getSpeechRecognitionCtor();
    setSupported(ctorRef.current !== null);
  }, []);

  useEffect(() => () => recognitionRef.current?.stop(), []);

  const toggle = useCallback(() => {
    const Ctor = ctorRef.current;
    if (!Ctor) return;
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }
    const recognition = new Ctor();
    recognition.lang = RECOGNITION_LANG[language];
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript;
      if (transcript) onResultRef.current(transcript);
    };
    recognition.onerror = () => setListening(false);
    recognition.onend = () => setListening(false);
    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  }, [language, listening]);

  return { supported, listening, toggle };
}

const SYNTH_LANG: Record<LanguageCode, string> = { en: "en-IN", hi: "hi-IN", gu: "gu-IN" };

/**
 * Natural-voice selection for the Web Speech API. Browsers ship a mix of
 * high-quality cloud/neural voices ("Google US English", "Google हिन्दी",
 * platform "Natural"/"Enhanced"/"Siri" voices) alongside a low-quality local
 * fallback (often an eSpeak-family "compact" voice) — the naive `getVoices()
 * .find(lang match)` tends to land on whichever the browser lists first,
 * which is frequently the robotic one. This ranks candidates by name against
 * a per-language preference list and actively deprioritizes eSpeak/compact
 * voices instead of picking them by accident.
 */
const VOICE_PREFERENCE_KEYWORDS: Record<LanguageCode, string[]> = {
  en: [
    "google us english",
    "google uk english",
    "google",
    "natural",
    "neural",
    "premium",
    "enhanced",
    "siri",
    "samantha",
    "aaron",
    "ava",
  ],
  hi: ["google", "natural", "neural", "premium", "enhanced", "siri"],
  gu: ["google", "natural", "neural", "premium", "enhanced", "siri"],
};

const VOICE_AVOID_KEYWORDS = ["espeak", "compact"];

/** Fixed demo voice identity. These are Chrome's Google voiceURI values.
 * A fallback stays browser-only when a judge's Chrome lacks Google Gujarati. */
const PINNED_VOICE_URIS: Record<LanguageCode, string[]> = {
  en: ["Google US English"],
  hi: ["Google हिन्दी"],
  gu: ["Google ગુજરાતી", "Google हिन्दी"],
};

function scoreVoiceName(name: string, language: LanguageCode): number {
  const lower = name.toLowerCase();
  if (VOICE_AVOID_KEYWORDS.some((bad) => lower.includes(bad))) return -100;
  const keywords = VOICE_PREFERENCE_KEYWORDS[language];
  for (let i = 0; i < keywords.length; i++) {
    if (lower.includes(keywords[i])) return keywords.length - i;
  }
  return 0;
}

/** Voices rarely include `gu-IN`; Hindi is the closest phonetic fallback so
 * Gujarati still gets a real voice instead of whatever locale-less default
 * the browser would otherwise pick. */
function candidateVoicesForLanguage(voices: SpeechSynthesisVoice[], language: LanguageCode): SpeechSynthesisVoice[] {
  const prefix = SYNTH_LANG[language].split("-")[0];
  const matches = voices.filter((v) => v.lang.toLowerCase().startsWith(prefix));
  if (matches.length > 0 || language !== "gu") return matches;
  return voices.filter((v) => v.lang.toLowerCase().startsWith("hi"));
}

const naturalVoiceCache = new Map<LanguageCode, SpeechSynthesisVoice>();
let voiceschangedListenerBound = false;

/** Picks the most natural available voice for `language`, caching the
 * result. Returns `null` (never throws) if speechSynthesis is unavailable
 * or the voice list hasn't populated yet — callers fall back to the
 * browser's own `lang`-based default in that case. Exported so the Voice
 * Call channel demo (VoiceCallPlayerCard) can reuse the same selection. */
export function pickNaturalVoice(language: LanguageCode): SpeechSynthesisVoice | null {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return null;
  if (!voiceschangedListenerBound) {
    voiceschangedListenerBound = true;
    // Voice lists often populate after first paint. Clear the early cache so
    // the browser can use its normal, higher-quality voice once available.
    window.speechSynthesis.addEventListener("voiceschanged", () => naturalVoiceCache.clear());
  }

  const cached = naturalVoiceCache.get(language);
  if (cached) return cached;
  const voices = window.speechSynthesis.getVoices();
  if (voices.length === 0) return null;

  const pinned = PINNED_VOICE_URIS[language]
    .map((voiceURI) => voices.find((voice) => voice.voiceURI === voiceURI))
    .find((voice): voice is SpeechSynthesisVoice => Boolean(voice));
  if (pinned) {
    naturalVoiceCache.set(language, pinned);
    return pinned;
  }

  // The pinned URI is a browser capability, not a guarantee on another
  // judge's device. Fall back to the existing quality-ranked selection when
  // Chrome does not expose it rather than losing speech playback entirely.
  const candidates = candidateVoicesForLanguage(voices, language);
  if (candidates.length === 0) return null;
  const best = candidates.reduce((a, b) => (scoreVoiceName(b.name, language) > scoreVoiceName(a.name, language) ? b : a));
  naturalVoiceCache.set(language, best);
  return best;
}

export interface UseSpeechOutputResult {
  supported: boolean;
  enabled: boolean;
  toggle: () => void;
  speak: (text: string, language: LanguageCode) => void;
}

/** Speech-synthesis toggle for companion replies. */
export function useSpeechOutput(): UseSpeechOutputResult {
  const [supported] = useState(() => typeof window !== "undefined" && "speechSynthesis" in window);
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    // Nudges the browser to populate getVoices() early so the first real
    // speak() call (which happens after the user taps to enable) is more
    // likely to already have the natural voice ranked and cached.
    if (supported) window.speechSynthesis.getVoices();
  }, [supported]);

  const speak = useCallback(
    (text: string, language: LanguageCode) => {
      if (!supported || !enabled || !text.trim()) return;
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = SYNTH_LANG[language];
      utterance.rate = 0.97;
      utterance.pitch = 1.0;
      const voice = pickNaturalVoice(language);
      if (voice) utterance.voice = voice;
      window.speechSynthesis.speak(utterance);
    },
    [supported, enabled]
  );

  const toggle = useCallback(() => {
    if (!supported) return;
    setEnabled((prev) => {
      if (prev) window.speechSynthesis.cancel();
      return !prev;
    });
  }, [supported]);

  return { supported, enabled, toggle, speak };
}
