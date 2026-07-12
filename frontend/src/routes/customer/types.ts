/**
 * Local types for the customer chat surface. `lib/types.ts` (C.6/C.8) is the
 * cross-surface contract source of truth, but two backend responses differ
 * from what it declares there (confirmed against the actual FastAPI routes,
 * not assumed): `POST /sessions` returns `greeting` as a frame *list*, not a
 * string, and the `done` frame carries an extra optional `error` field. This
 * surface is scoped to `routes/customer/` + `components/chat/`, so rather
 * than edit the shared contract file, the corrected shapes live here.
 */
import type { AvatarState, CardType, ChatCard } from "@/lib/types";

export type ChatSseFrame =
  | { type: "token"; text: string }
  | { type: "card"; card: ChatCard }
  | { type: "avatar"; state: Exclude<AvatarState, "idle" | "listening"> }
  | { type: "done"; audit_ref: string; error?: boolean };

export interface SessionCreateResponse {
  session_id: string;
  greeting: ChatSseFrame[];
}

/** Roster shape actually returned by `GET /api/personas` — a summary card,
 * not the full `Persona` (profile+transactions+goals+external) the shared
 * type declares. */
export interface PersonaRosterItem {
  id: string;
  name: string;
  age: number;
  city: string;
  segment: string;
  language: string;
  avatar: string;
  story: string;
}

export type ChatRole = "user" | "companion";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  ts: string;
  /** Present once at least one token has arrived for this turn. */
  text?: string;
  /** True while a companion text message is still receiving tokens. */
  streaming?: boolean;
  card?: ChatCard;
  /** A turn-level failure (`done.error`) with no usable reply text. */
  error?: boolean;
  /** The user text to resend, only set on error messages. */
  retryText?: string;
}

export const CARD_TYPES: readonly CardType[] = [
  "spend_summary",
  "recommendation",
  "routed_to_rm",
  "execution_confirm",
  "execution_receipt",
  "aa_connect",
  "goal",
  "literacy",
  "nudge",
  "distress_support",
] as const;
