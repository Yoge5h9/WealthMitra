/** Shared shape the four channel-playback cards render from. */
export interface ChannelDelivery {
  title: string;
  body: string;
  personaName: string;
  language: string;
  /** True when this is the built-in fallback copy, not real AI-generated nudge text. */
  sample: boolean;
}
