import type { ChatCard } from "@/lib/types";
import { SpendSummaryCard } from "@/components/chat/cards/SpendSummaryCard";
import { RecommendationCard } from "@/components/chat/cards/RecommendationCard";
import { RoutedToRmCard } from "@/components/chat/cards/RoutedToRmCard";
import { ExecutionConfirmCard } from "@/components/chat/cards/ExecutionConfirmCard";
import { ExecutionReceiptCard } from "@/components/chat/cards/ExecutionReceiptCard";
import { DistressSupportCard } from "@/components/chat/cards/DistressSupportCard";
import { LiteracyCard } from "@/components/chat/cards/LiteracyCard";
import { GoalCard } from "@/components/chat/cards/GoalCard";
import { NudgeCard } from "@/components/chat/cards/NudgeCard";
import { AaConnectCard } from "@/components/chat/cards/AaConnectCard";
import { GenericCard } from "@/components/chat/cards/GenericCard";
import type {
  AaConnectCard as AaConnectCardData,
  DistressSupportCard as DistressSupportCardData,
  ExecutionConfirmCard as ExecutionConfirmCardData,
  ExecutionReceiptCard as ExecutionReceiptCardData,
  GoalCard as GoalCardData,
  LiteracyCard as LiteracyCardData,
  NudgeCard as NudgeCardData,
  RecommendationCard as RecommendationCardData,
  RoutedToRmCard as RoutedToRmCardData,
  SpendSummaryCard as SpendSummaryCardData,
} from "@/components/chat/cards/types";

export interface CardRouterProps {
  card: ChatCard;
  sessionId?: string | null;
  onSendMessage?: (text: string) => void;
  onOpenAudit?: () => void;
  /** Disables product-touching CTAs while a turn is still streaming. */
  sending?: boolean;
}

/** Dispatches a `card_type` to its dedicated renderer. An unrecognized
 * type — including forward-compatible additions to the backend contract —
 * falls back to `GenericCard` instead of crashing the thread. */
export function CardRouter({ card, sessionId, onSendMessage, onOpenAudit, sending }: CardRouterProps) {
  switch (card.card_type) {
    case "spend_summary":
      return <SpendSummaryCard card={card as SpendSummaryCardData} />;

    case "recommendation":
      return (
        <RecommendationCard
          card={card as RecommendationCardData}
          disabled={sending}
          onRequestProduct={(name) => onSendMessage?.(`I'd like to proceed with ${name}.`)}
        />
      );

    case "routed_to_rm":
      return <RoutedToRmCard card={card as RoutedToRmCardData} />;

    case "execution_confirm":
      return (
        <ExecutionConfirmCard card={card as ExecutionConfirmCardData} sessionId={sessionId ?? null} onOpenAudit={onOpenAudit} />
      );

    case "execution_receipt":
      return <ExecutionReceiptCard receipt={cardToReceipt(card as ExecutionReceiptCardData)} onOpenAudit={onOpenAudit} />;

    case "distress_support":
      return (
        <DistressSupportCard card={card as DistressSupportCardData} onPickOption={(option) => onSendMessage?.(option)} />
      );

    case "literacy":
      return <LiteracyCard card={card as LiteracyCardData} />;

    case "goal":
      return <GoalCard card={card as GoalCardData} />;

    case "nudge":
      return <NudgeCard card={card as NudgeCardData} />;

    case "aa_connect":
      return <AaConnectCard card={card as AaConnectCardData} />;

    default:
      return <GenericCard card={card} />;
  }
}

function cardToReceipt(card: ExecutionReceiptCardData) {
  return {
    receipt_id: card.receipt_id,
    session_id: "",
    product_id: "",
    product_name: card.product_name,
    amount: card.amount,
    executed_at: card.executed_at,
    audit_ref: card.audit_ref,
  };
}
