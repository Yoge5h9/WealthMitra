/**
 * Demo-only presentation layer for the fixed synthetic roster. It makes the
 * already persona-aware backend behaviour visible across chat, dashboard and
 * channels without treating assumptions as financial facts or preferences.
 */
export type ChannelKey = "push" | "sms" | "message" | "voice";

export interface PersonaExperience {
  chat: {
    label: string;
    description: string;
    companionBubbleClass: string;
    userBubbleClass: string;
  };
  dashboard: {
    title: string;
    description: string;
    primary: "cashflow" | "holdings" | "goals";
    accentClass: string;
  };
  channels: {
    preference: string;
    cadence: string;
    rationale: string;
    fits: Record<ChannelKey, { label: string; reason: string; emphasis: "primary" | "supporting" | "opt_in" }>;
  };
}

const DEFAULT: PersonaExperience = {
  chat: {
    label: "Plain-language, customer-led",
    description: "Short explanations, with the customer choosing language and voice.",
    companionBubbleClass: "border-structural-200 bg-structural-50",
    userBubbleClass: "bg-structural-600 text-neutral-0",
  },
  dashboard: {
    title: "Start with what matters today",
    description: "The dashboard will become more specific as the customer shares data and goals.",
    primary: "cashflow",
    accentClass: "border-structural-200 bg-structural-50 text-structural-800",
  },
  channels: {
    preference: "In-app first",
    cadence: "Only when useful and permissioned",
    rationale: "The customer controls how WealthMitra communicates as their profile develops.",
    fits: {
      push: { label: "Supporting", reason: "A gentle prompt when there is something useful to review.", emphasis: "supporting" },
      sms: { label: "Supporting", reason: "A concise fallback for important reminders.", emphasis: "supporting" },
      message: { label: "Primary", reason: "A familiar place to continue a short conversation.", emphasis: "primary" },
      voice: { label: "Opt-in", reason: "Available when a spoken explanation is preferred.", emphasis: "opt_in" },
    },
  },
};

const EXPERIENCES: Record<string, PersonaExperience> = {
  ravi: {
    chat: { label: "Quick, visual and action-led", description: "Short check-ins that fit a busy salary routine.", companionBubbleClass: "border-structural-200 bg-structural-50", userBubbleClass: "bg-structural-600 text-neutral-0" },
    dashboard: { title: "Keep your monthly plan on track", description: "Cash flow, surplus and the next small investing step come first for this steady salary profile.", primary: "cashflow", accentClass: "border-structural-200 bg-structural-50 text-structural-800" },
    channels: { preference: "Mobile push + message", cadence: "Short, salary-window check-ins", rationale: "Ravi’s profile benefits from fast, skimmable actions rather than a long call.", fits: { push: { label: "Primary", reason: "A quick, visual cue for a timely money moment.", emphasis: "primary" }, sms: { label: "Supporting", reason: "A concise fallback for time-sensitive reminders.", emphasis: "supporting" }, message: { label: "Primary", reason: "Lets Ravi continue with a question when convenient.", emphasis: "primary" }, voice: { label: "Opt-in", reason: "Only if Ravi chooses a spoken walkthrough.", emphasis: "opt_in" } } } },
  priya: {
    chat: { label: "Simple, supportive and small-step", description: "Plain Hindi and flexible next steps that respect variable income.", companionBubbleClass: "border-warning-200 bg-warning-50", userBubbleClass: "bg-warning-500 text-neutral-950" },
    dashboard: { title: "See this week’s breathing room", description: "Cash flow and a practical buffer are clearer than a dense portfolio view for variable income.", primary: "cashflow", accentClass: "border-warning-200 bg-warning-50 text-neutral-800" },
    channels: { preference: "Hindi message + SMS", cadence: "Income-triggered, never fixed-pressure", rationale: "Priya receives short, supportive check-ins only when her income context makes them relevant.", fits: { push: { label: "Supporting", reason: "Useful for a lightweight in-app reminder.", emphasis: "supporting" }, sms: { label: "Primary", reason: "A concise Hindi reminder works even when data is limited.", emphasis: "primary" }, message: { label: "Primary", reason: "A simple Hindi conversation can continue at her pace.", emphasis: "primary" }, voice: { label: "Opt-in", reason: "Available for a spoken explanation, never assumed.", emphasis: "opt_in" } } } },
  shanta: {
    chat: { label: "Patient, step-by-step and voice-friendly", description: "Plain Hindi with fewer choices at a time and no rushed decisions.", companionBubbleClass: "border-success-200 bg-success-50", userBubbleClass: "bg-success-600 text-neutral-0" },
    dashboard: { title: "Protect the plan you rely on", description: "Goals, predictable cash flow and simple explanations take priority over a dense data view.", primary: "goals", accentClass: "border-success-200 bg-success-50 text-success-900" },
    channels: { preference: "Hindi voice + SMS", cadence: "Slow, opt-in and only for meaningful moments", rationale: "Shanta’s experience prioritises clear, spoken explanations and a simple written fallback.", fits: { push: { label: "Supporting", reason: "A small reminder, never the only explanation.", emphasis: "supporting" }, sms: { label: "Primary", reason: "A simple Hindi record she can revisit.", emphasis: "primary" }, message: { label: "Supporting", reason: "Available if she prefers a chat thread.", emphasis: "supporting" }, voice: { label: "Primary", reason: "A patient, step-by-step explanation when she opts in.", emphasis: "primary" } } } },
  meera: {
    chat: { label: "Concise, Gujarati and business-context aware", description: "Focus on liquidity, timing and decisions without unnecessary basics.", companionBubbleClass: "border-brand-200 bg-brand-50", userBubbleClass: "bg-brand-500 text-neutral-950" },
    dashboard: { title: "Keep business and personal liquidity visible", description: "Connected holdings and cash positioning come first for a business owner’s decision context.", primary: "holdings", accentClass: "border-brand-200 bg-brand-50 text-neutral-800" },
    channels: { preference: "Gujarati message + scheduled RM callback", cadence: "Business-cycle summaries, not frequent pings", rationale: "Meera gets concise, decision-ready context and a specialist conversation when needed.", fits: { push: { label: "Supporting", reason: "A short cue for a material change.", emphasis: "supporting" }, sms: { label: "Supporting", reason: "A compact reminder if a decision needs attention.", emphasis: "supporting" }, message: { label: "Primary", reason: "Supports a concise Gujarati exchange around a business moment.", emphasis: "primary" }, voice: { label: "Opt-in", reason: "Reserved for a scheduled specialist conversation.", emphasis: "opt_in" } } } },
  devika: {
    chat: { label: "Concise, portfolio-level and RM-ready", description: "Assumes financial fluency while keeping complex decisions with a specialist.", companionBubbleClass: "border-neutral-300 bg-neutral-50", userBubbleClass: "bg-neutral-800 text-neutral-0" },
    dashboard: { title: "Scan the whole portfolio, then go deeper", description: "Holdings and material changes lead; complex decisions are prepared for an RM, not auto-sold.", primary: "holdings", accentClass: "border-neutral-300 bg-neutral-100 text-neutral-900" },
    channels: { preference: "Dashboard + scheduled RM callback", cadence: "Material-change only", rationale: "Devika sees concise portfolio context first and uses a specialist conversation for complex choices.", fits: { push: { label: "Supporting", reason: "Only for a material portfolio event.", emphasis: "supporting" }, sms: { label: "Opt-in", reason: "Not the default for detailed portfolio context.", emphasis: "opt_in" }, message: { label: "Supporting", reason: "A concise follow-up after a dashboard insight.", emphasis: "supporting" }, voice: { label: "Primary", reason: "A scheduled RM conversation for specialised decisions.", emphasis: "primary" } } } },
  arjun: {
    chat: { label: "Asynchronous, precise and NRI-context aware", description: "Clear residency and remittance context without assuming a live call is convenient.", companionBubbleClass: "border-structural-200 bg-neutral-50", userBubbleClass: "bg-structural-700 text-neutral-0" },
    dashboard: { title: "Keep your India wealth picture connected", description: "External holdings and cross-border context come first, with no assumptions about residency eligibility.", primary: "holdings", accentClass: "border-structural-200 bg-neutral-50 text-structural-800" },
    channels: { preference: "Asynchronous message + timezone-aware push", cadence: "Customer-timezone aware, never a surprise call", rationale: "Arjun can review precise NRI context when convenient, regardless of time zone.", fits: { push: { label: "Primary", reason: "A timezone-aware prompt for something worth reviewing.", emphasis: "primary" }, sms: { label: "Supporting", reason: "A brief backup for an important update.", emphasis: "supporting" }, message: { label: "Primary", reason: "Lets the conversation continue asynchronously.", emphasis: "primary" }, voice: { label: "Opt-in", reason: "Only on a time the customer chooses.", emphasis: "opt_in" } } } },
  vikram: {
    chat: { label: "Calm, supportive and no-selling", description: "When money feels tight, the companion focuses on clarity and support—not products.", companionBubbleClass: "border-warning-200 bg-warning-50", userBubbleClass: "bg-neutral-700 text-neutral-0" },
    dashboard: { title: "Start with essentials and breathing room", description: "Cash flow is presented as support; product outreach stays suppressed during financial stress.", primary: "cashflow", accentClass: "border-warning-200 bg-warning-50 text-neutral-800" },
    channels: { preference: "Support-only in app", cadence: "No product outreach during distress", rationale: "The protective path suppresses selling and keeps communication practical and optional.", fits: { push: { label: "Opt-in", reason: "Only a supportive, non-product reminder.", emphasis: "opt_in" }, sms: { label: "Opt-in", reason: "Only if a support reminder is requested.", emphasis: "opt_in" }, message: { label: "Primary", reason: "A private, supportive conversation when the customer chooses.", emphasis: "primary" }, voice: { label: "Opt-in", reason: "Available for support, never as a sales call.", emphasis: "opt_in" } } } },
};

export function personaExperienceFor(personaId: string | null | undefined): PersonaExperience {
  return (personaId && EXPERIENCES[personaId]) || DEFAULT;
}
