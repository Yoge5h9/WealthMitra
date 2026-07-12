import { Cell, Pie, PieChart, Tooltip } from "recharts";
import { PiggyBank } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MoneyText } from "@/components/shared/MoneyText";
import { ChartContainer, ChartTooltip, chartColor } from "@/components/shared/ChartTheme";
import { formatINR } from "@/lib/format";
import type { SpendSummaryCard as SpendSummaryCardData } from "./types";

export function SpendSummaryCard({ card }: { card: SpendSummaryCardData }) {
  const categories = Object.entries(card.spend_by_category)
    .filter(([, amount]) => amount > 0)
    .sort(([, a], [, b]) => b - a);
  const total = categories.reduce((sum, [, amount]) => sum + amount, 0);
  const chartData = categories.map(([category, amount]) => ({ name: category, value: amount }));

  return (
    <Card className="border border-neutral-200">
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-structural-600">
            <PiggyBank size={18} strokeWidth={1.75} />
            <CardTitle>
              <span className="font-display text-h4 text-neutral-900">Where your money went</span>
            </CardTitle>
          </div>
          <span className="rounded-full bg-success-50 px-2 py-1 text-caption font-semibold text-success-700">
            {(card.savings_rate * 100).toFixed(0)}% saved
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <MoneyText value={card.monthly_income} size="lg" className="mb-4" whyThisNumber="Computed from your last 3 months of credited income." />

        {categories.length === 0 ? (
          <p className="text-body-sm text-neutral-600">No spend recorded for this period yet.</p>
        ) : (
          <div className="grid grid-cols-[112px_1fr] items-center gap-4">
            <ChartContainer height={112}>
              <PieChart>
                <Pie
                  data={chartData}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={34}
                  outerRadius={54}
                  paddingAngle={2}
                  stroke="none"
                >
                  {chartData.map((entry, index) => (
                    <Cell key={entry.name} fill={chartColor(index)} />
                  ))}
                </Pie>
                <Tooltip content={<ChartTooltip valueFormatter={(v) => formatINR(v, { compact: true })} />} />
              </PieChart>
            </ChartContainer>

            {/* min-w-0: a grid item's min-width defaults to its content, which
                would push the amounts past the card's clipped edge. */}
            <ul className="min-w-0 space-y-2">
              {categories.slice(0, 5).map(([category, amount], index) => (
                <li key={category} className="flex min-w-0 items-center gap-2">
                  <span className="size-2 shrink-0 rounded-full" style={{ background: chartColor(index) }} />
                  <span className="min-w-0 flex-1 truncate text-body-sm capitalize text-neutral-700">
                    {category.replace(/_/g, " ")}
                  </span>
                  <span className="shrink-0 text-caption tabular-nums text-neutral-500">
                    {total > 0 ? `${Math.round((amount / total) * 100)}%` : ""}
                  </span>
                  <MoneyText value={amount} size="sm" compact className="shrink-0" />
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
