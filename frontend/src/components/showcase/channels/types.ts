/** Shared shape the four channel-playback cards render from. */
export type ChannelKey = "push" | "sms" | "message" | "voice";

export interface ChannelFit {
  label: string;
  reason: string;
  emphasis: "primary" | "supporting" | "opt_in";
}

export interface ChannelDelivery {
  title: string;
  body: string;
  personaName: string;
  language: string;
  /** True when this is the built-in fallback copy, not real AI-generated nudge text. */
  sample: boolean;
  communicationPreference: string;
  cadence: string;
  channelFits: Record<ChannelKey, ChannelFit>;
}
