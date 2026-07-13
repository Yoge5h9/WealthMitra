/**
 * Suggested-prompt chips: persona-aware, localized. Keyed by the seven seed
 * persona ids in `data/synthetic/` (segment + language noted alongside each
 * for the fallback lookup) so the row always reads as "written for this
 * person," not a generic three-bullet placeholder.
 */
import type { LanguageCode } from "@/components/shared/LangToggle";

const BY_PERSONA: Record<string, string[]> = {
  // mass_retail_salaried · en
  ravi: ["Where did my money go last month?", "Start a SIP", "Am I saving enough?"],
  vikram: ["How much can I invest every month?", "FD vs SIP — which is better for me?"],
  // senior · hi
  shanta: ["मेरी FD कब मैच्योर होगी?", "मुझे कितना ब्याज मिलेगा?", "NPS क्या है?"],
  // mass_retail_gig · hi
  priya: ["मेरी अनियमित कमाई से मैं कैसे बचत करूं?", "इमरजेंसी फंड कैसे बनाऊं?"],
  // affluent · gu
  meera: ["શું મારે ઇક્વિટીમાં રોકાણ કરવું જોઈએ?", "મારો પોર્ટફોલિયો કેવો છે?"],
  // nri · en
  arjun: ["How should I invest in India as an NRI?", "What are the tax rules for me?"],
  // hni · en
  devika: ["What premium investment options do I have?", "Show me my portfolio diversification"],
};

const BY_LANGUAGE: Record<LanguageCode, string[]> = {
  en: ["Where did my money go last month?", "What can I invest in?", "Am I on track for my goals?"],
  hi: ["मेरा पैसा कहाँ खर्च हुआ?", "मैं कहाँ निवेश कर सकता/सकती हूँ?"],
  gu: ["મારા પૈસા ક્યાં ખર્ચાયા?", "હું ક્યાં રોકાણ કરી શકું?"],
};

// new_to_idbi has no persona seed yet, so its chips invite onboarding
// (money picture, progress, investing, AA connect) rather than assume the
// per-persona facts the other rows are written against.
const NEW_TO_IDBI_CHIPS: Record<LanguageCode, string[]> = {
  en: ["Tell me about my money", "How am I doing?", "I want to start investing", "Connect my accounts"],
  hi: ["मेरे पैसों के बारे में बताएं", "मैं कैसा कर रहा/रही हूं?", "मैं निवेश शुरू करना चाहता/चाहती हूं", "मेरे खाते जोड़ें"],
  gu: ["મારા પૈસા વિશે જણાવો", "હું કેવું કરી રહ્યો/રહી છું?", "મારે રોકાણ શરૂ કરવું છે", "મારા ખાતા જોડો"],
};

/** Suggested prompts for a persona in a given (possibly toggled) language. */
export function chipsFor(personaId: string, language: LanguageCode): string[] {
  if (personaId === "new_to_idbi") return NEW_TO_IDBI_CHIPS[language] ?? NEW_TO_IDBI_CHIPS.en;
  const known = BY_PERSONA[personaId];
  if (known && language === (personaId === "meera" ? "gu" : personaId === "shanta" || personaId === "priya" ? "hi" : "en")) {
    return known;
  }
  return BY_LANGUAGE[language] ?? BY_LANGUAGE.en;
}
