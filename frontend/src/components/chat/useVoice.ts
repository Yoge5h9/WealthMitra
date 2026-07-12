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

export interface UseSpeechOutputResult {
  supported: boolean;
  enabled: boolean;
  toggle: () => void;
  speak: (text: string, language: LanguageCode) => void;
}

/** Speech-synthesis toggle for companion replies. Best-effort hi-IN/gu-IN
 * voice match; falls back silently to whatever voice the browser defaults
 * to for that `lang` (never throws if a regional voice isn't installed). */
export function useSpeechOutput(): UseSpeechOutputResult {
  const [supported] = useState(() => typeof window !== "undefined" && "speechSynthesis" in window);
  const [enabled, setEnabled] = useState(false);

  const speak = useCallback(
    (text: string, language: LanguageCode) => {
      if (!supported || !enabled || !text.trim()) return;
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = SYNTH_LANG[language];
      const voices = window.speechSynthesis.getVoices();
      const match = voices.find((v) => v.lang === utterance.lang) ?? voices.find((v) => v.lang.startsWith(language));
      if (match) utterance.voice = match;
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
