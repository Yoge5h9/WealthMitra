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
const VOICE_PIN_KEY = "wm_voice_pin";

function savedVoiceUri(language: LanguageCode): string | null {
  try {
    const saved = window.sessionStorage.getItem(`${VOICE_PIN_KEY}_${language}`);
    return saved || null;
  } catch {
    return null;
  }
}

function pinVoice(language: LanguageCode, voice: SpeechSynthesisVoice): SpeechSynthesisVoice {
  naturalVoiceCache.set(language, voice);
  try {
    window.sessionStorage.setItem(`${VOICE_PIN_KEY}_${language}`, voice.voiceURI);
  } catch {
    // Session storage is a consistency enhancement, never a dependency.
  }
  return voice;
}

function preferredVoice(voices: SpeechSynthesisVoice[], language: LanguageCode): SpeechSynthesisVoice | null {
  const pinnedUri = savedVoiceUri(language);
  const pinned = pinnedUri ? voices.find((voice) => voice.voiceURI === pinnedUri) : null;
  if (pinned) return pinVoice(language, pinned);

  const cached = naturalVoiceCache.get(language);
  const cacheMatch = cached ? voices.find((voice) => voice.voiceURI === cached.voiceURI) : null;
  if (cacheMatch) return cacheMatch;

  const candidates = candidateVoicesForLanguage(voices, language);
  if (candidates.length === 0) return null;
  const best = candidates.reduce((a, b) => (scoreVoiceName(b.name, language) > scoreVoiceName(a.name, language) ? b : a));
  return pinVoice(language, best);
}

/** Picks the most natural available voice for `language`, caching the
 * result. Returns `null` (never throws) if speechSynthesis is unavailable
 * or the voice list hasn't populated yet — callers fall back to the
 * browser's own `lang`-based default in that case. Exported so the Voice
 * Call channel demo (VoiceCallPlayerCard) can reuse the same selection. */
export function pickNaturalVoice(language: LanguageCode): SpeechSynthesisVoice | null {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return null;
  const voices = window.speechSynthesis.getVoices();
  if (voices.length === 0) return null;
  return preferredVoice(voices, language);
}

/** Resolves and pins a natural voice before an utterance is started. Browsers
 * often populate their voices asynchronously; waiting briefly prevents one
 * screen from falling back to a browser default while another gets the
 * selected natural voice for the same language. */
export function resolveNaturalVoice(language: LanguageCode): Promise<SpeechSynthesisVoice | null> {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return Promise.resolve(null);
  const synthesis = window.speechSynthesis;
  const immediate = preferredVoice(synthesis.getVoices(), language);
  if (immediate) return Promise.resolve(immediate);

  return new Promise((resolve) => {
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timeout);
      synthesis.removeEventListener("voiceschanged", onVoicesChanged);
      resolve(preferredVoice(synthesis.getVoices(), language));
    };
    const onVoicesChanged = () => finish();
    const timeout = window.setTimeout(finish, 500);
    synthesis.addEventListener("voiceschanged", onVoicesChanged);
  });
}

/** Starts an utterance only after it has the same pinned natural voice used
 * throughout the corresponding language experience. */
export async function speakWithNaturalVoice(utterance: SpeechSynthesisUtterance, language: LanguageCode): Promise<boolean> {
  const voice = await resolveNaturalVoice(language);
  if (!voice) return false;
  utterance.voice = voice;
  window.speechSynthesis.speak(utterance);
  return true;
}

export interface UseSpeechOutputResult {
  supported: boolean;
  enabled: boolean;
  toggle: () => void;
  speak: (text: string, language: LanguageCode) => void;
}

/** Speech-synthesis toggle for companion replies. It waits for and pins the
 * same natural voice that the AI-call playback uses for each language. */
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
      void speakWithNaturalVoice(utterance, language);
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
