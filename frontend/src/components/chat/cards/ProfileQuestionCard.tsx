import { ClipboardList } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ProfileQuestionCard as ProfileQuestionCardData } from "./types";

export function ProfileQuestionCard({ card, onPick, disabled }: { card: ProfileQuestionCardData; onPick: (answer: string) => void; disabled?: boolean }) {
  return (
    <Card className="border border-structural-200 bg-structural-50">
      <CardHeader>
        <div className="flex items-center gap-2 text-structural-700">
          <ClipboardList size={20} strokeWidth={1.75} aria-hidden="true" />
          <CardTitle><span className="font-display text-h4 text-neutral-900">Build your starting profile</span></CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-caption font-medium text-structural-700">Question {card.step} of {card.total_steps}</p>
        <p className="text-body font-medium text-neutral-900">{card.question}</p>
        <div className="grid gap-2">
          {card.options.map((option) => (
            <Button key={option} size="touch" variant="outline" className="justify-start text-left" disabled={disabled} onClick={() => onPick(option)}>{option}</Button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
