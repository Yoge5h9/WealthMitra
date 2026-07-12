import type { Nudge, NudgeKind } from "@/lib/types";
import type { ChannelDelivery, ChannelMessage } from "./types";
import type { PersonaExperience } from "@/lib/personaExperience";

interface ChannelVoice {
  messageLead: string;
  action: string;
  voiceLead: string;
  aaInvite?: string;
}

const VOICE_BY_PERSONA: Record<string, ChannelVoice> = {
  ravi: { messageLead: "Quick salary-day check-in.", action: "Open WealthMitra when you have two minutes.", voiceLead: "Here is a quick money check-in.", aaInvite: "You can also connect eligible external accounts through Account Aggregator for one combined view." },
  priya: { messageLead: "एक छोटा, आसान चेक-इन।", action: "जब सुविधाजनक हो, WealthMitra में देखें।", voiceLead: "आपकी अनियमित कमाई के हिसाब से एक छोटा अपडेट है।" },
  shanta: { messageLead: "आराम से देखिए, कोई जल्दी नहीं है।", action: "जब ठीक लगे, WealthMitra में धीरे-धीरे देखें।", voiceLead: "मैं एक सरल और छोटा अपडेट साझा कर रही हूँ।", aaInvite: "अगर आप चाहें, तो Account Aggregator से दूसरे खाते जोड़कर पूरी तस्वीर एक जगह देख सकती हैं।" },
  meera: { messageLead: "તમારા વ્યવસાયના નાણાં માટે એક ટૂંકો ચેક-ઇન.", action: "અનુકૂળ હોય ત્યારે WealthMitraમાં જુઓ.", voiceLead: "તમારી લિક્વિડિટી માટે એક સંક્ષિપ્ત અપડેટ છે.", aaInvite: "ઇચ્છો તો Account Aggregator દ્વારા બહારના એકાઉન્ટ જોડીને સંપૂર્ણ દૃશ્ય જોઈ શકો છો." },
  devika: { messageLead: "A concise portfolio check-in.", action: "Review it in WealthMitra when convenient.", voiceLead: "Here is the material point from your wealth view.", aaInvite: "You can connect eligible external accounts through Account Aggregator for a fuller portfolio view." },
  arjun: { messageLead: "A quick India-wealth update, for your time zone.", action: "Review it whenever convenient in WealthMitra.", voiceLead: "Here is a short India-wealth update.", aaInvite: "You can connect eligible external accounts through Account Aggregator for one combined India wealth view." },
  vikram: { messageLead: "A private support check-in.", action: "Open WealthMitra only when you are ready.", voiceLead: "This is a supportive update, with no product offer." },
};

const DEFAULT_VOICE: ChannelVoice = {
  messageLead: "A quick WealthMitra check-in.",
  action: "Open WealthMitra when convenient.",
  voiceLead: "Here is a short update from WealthMitra.",
};

function fitText(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max - 1).trimEnd()}…` : text;
}

/**
 * One nudge has one audited financial fact set. Each channel gets its own
 * presentation around that same fact set: concise push, record-like SMS,
 * conversational message, and spoken call. No amount or percentage is
 * created or changed here.
 */
export function composeChannelDelivery(
  personaId: string,
  personaName: string,
  nudge: Nudge,
  experience: PersonaExperience,
): ChannelDelivery {
  const voice = VOICE_BY_PERSONA[personaId] ?? DEFAULT_VOICE;
  const functional = nudge.kind === "functional";
  const suffix = functional ? voice.action : "No action is needed — this is simply your check-in.";
  const aaSuffix = functional && voice.aaInvite ? ` ${voice.aaInvite}` : "";
  const push: ChannelMessage = { title: nudge.title, body: fitText(nudge.body, 118) };
  const sms: ChannelMessage = { title: "IDBI WealthMitra", body: fitText(`${nudge.body} ${suffix}`, 150) };
  const message: ChannelMessage = { title: voice.messageLead, body: `${nudge.body} ${suffix}${aaSuffix}` };
  const call: ChannelMessage = { title: "WealthMitra call", body: `Hi ${personaName}. ${voice.voiceLead} ${nudge.body} ${suffix}${aaSuffix}` };

  return {
    personaName,
    language: nudge.language,
    sample: nudge.id.startsWith("sample_"),
    communicationPreference: experience.channels.preference,
    cadence: experience.channels.cadence,
    channelFits: experience.channels.fits,
    messages: { push, sms, message, voice: call },
  };
}

export function sampleChannelNudges(personaId: string, personaName: string, language: string): Record<NudgeKind, Nudge> {
  const copy: Record<string, Record<NudgeKind, { title: string; body: string }>> = {
    ravi: { functional: { title: "Your salary plan is ready", body: "Ravi, take a quick look at this month’s surplus and next step." }, relational: { title: "A steady saving habit", body: "Ravi, your regular progress is worth noticing." } },
    priya: { functional: { title: "एक छोटा बचत कदम", body: "प्रिया, अपनी कमाई के हिसाब से आज का छोटा अगला कदम देखें।" }, relational: { title: "आपकी कोशिश मायने रखती है", body: "प्रिया, छोटी-छोटी बचत भी धीरे-धीरे मजबूत आधार बनाती है।" } },
    shanta: { functional: { title: "आज का सरल पैसा अपडेट", body: "शांता जी, अपनी बचत और खर्च का सरल सारांश देखें।" }, relational: { title: "आपकी योजना स्थिर है", body: "शांता जी, अपने लक्ष्य की ओर आपकी निरंतरता सराहनीय है।" } },
    meera: { functional: { title: "કેશ-ફ્લો ચેક-ઇન", body: "મીરા, વ્યવસાય અને વ્યક્તિગત લિક્વિડિટીનો ટૂંકો સારાંશ તૈયાર છે." }, relational: { title: "સારી નાણાકીય શિસ્ત", body: "મીરા, તમારી નિયમિત સમીક્ષા લાંબા ગાળે મદદરૂપ છે." } },
    devika: { functional: { title: "Portfolio review ready", body: "Devika, your concise wealth-view check-in is ready to review." }, relational: { title: "A disciplined wealth view", body: "Devika, your regular portfolio review is a strong long-term habit." } },
    arjun: { functional: { title: "India wealth view update", body: "Arjun, your India-focused wealth check-in is ready when you are." }, relational: { title: "Staying connected from abroad", body: "Arjun, keeping one clear India wealth view is a valuable habit." } },
    vikram: { functional: { title: "A private support check-in", body: "Vikram, review your cash-flow support options whenever you are ready." }, relational: { title: "One step at a time", body: "Vikram, you do not have to solve everything at once." } },
  };
  const selected = copy[personaId] ?? { functional: { title: "Your WealthMitra update", body: `${personaName}, your next money check-in is ready.` }, relational: { title: "A quick check-in", body: `${personaName}, your progress matters.` } };
  const now = new Date().toISOString();
  return {
    functional: { id: "sample_functional", persona_id: personaId, kind: "functional", intent: "opportunity", language, source_metric_ids: [], created_at: now, ...selected.functional },
    relational: { id: "sample_relational", persona_id: personaId, kind: "relational", intent: "motivational", language, source_metric_ids: [], created_at: now, ...selected.relational },
  };
}
