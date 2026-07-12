import { Bar, BarChart, Cell, Pie, PieChart, Tooltip, XAxis, YAxis } from "recharts";
import { SectionHeader } from "@/components/shared/SectionHeader";
import { MoneyText } from "@/components/shared/MoneyText";
import { ChartContainer, ChartTick, ChartTooltip, chartColor } from "@/components/shared/ChartTheme";
import { formatINR } from "@/lib/format";
import { t, type LanguageCode } from "@/lib/i18n";
import { humanize } from "./format";

export interface SpendBreakdownProps {
  spendByCategory: Record<string, number>;
  monthlyIncome: number;
  monthlySurplus: number;
  language: LanguageCode;
}

/**
 * Category donut is a direct render of the real `spend_by_category` metric
 * (monthly-average debit spend per category). The engine only exposes one
 * averaged period per category — not a per-calendar-month ledger — so the
 * second chart shows this period's real income/spend/surplus split rather
 * than a fabricated multi-month trend (never invent a figure client-side).
 */
export function SpendBreakdown({ spendByCategory, monthlyIncome, monthlySurplus, language }: SpendBreakdownProps) {
  const rawCategories = Object.entries(spendByCategory)
    .filter(([, amount]) => amount > 0)
    .map(([category, amount]) => ({ category: humanize(category), amount }))
    .sort((a, b) => b.amount - a.amount);
  // The legend and donut must always describe exactly the same series. Keep
  // the five biggest categories legible, then combine the remainder rather
  // than drawing unlabeled, repeated-colour slivers.
  const remainder = rawCategories.slice(5).reduce((total, entry) => total + entry.amount, 0);
  const categories = [
    ...rawCategories.slice(0, 5),
    ...(remainder > 0 ? [{ category: t(language, "dashboard.spend.other"), amount: remainder }] : []),
  ];

  const monthlySpend = Math.max(monthlyIncome - monthlySurplus, 0);
  // `key` stays a stable, language-independent id for color lookup; `label`
  // is the translated string shown on the chart's x-axis.
  const cashflow = [
    { key: "income", label: t(language, "dashboard.spend.income"), amount: monthlyIncome },
    { key: "spend", label: t(language, "dashboard.spend.spend"), amount: monthlySpend },
    { key: "surplus", label: t(language, "dashboard.spend.surplus"), amount: Math.max(monthlySurplus, 0) },
  ];

  return (
    <div className="rounded-lg border border-neutral-200 bg-neutral-0 p-4">
      <SectionHeader
        eyebrow={t(language, "dashboard.spend.eyebrow")}
        title={t(language, "dashboard.spend.title")}
        description={t(language, "dashboard.spend.description")}
      />

      {categories.length === 0 ? (
        <p className="mt-4 text-body-sm text-neutral-600">{t(language, "dashboard.spend.noSpend")}</p>
      ) : (
        <>
          <div className="mt-2 flex items-center gap-4">
            <ChartContainer height={160} className="max-w-40">
              <PieChart>
                <Tooltip content={<ChartTooltip valueFormatter={(value) => formatINR(value, { compact: true })} />} />
                <Pie
                  data={categories}
                  dataKey="amount"
                  nameKey="category"
                  innerRadius={44}
                  outerRadius={72}
                  paddingAngle={2}
                  strokeWidth={0}
                >
                  {categories.map((entry, index) => (
                    <Cell key={entry.category} fill={chartColor(index)} />
                  ))}
                </Pie>
              </PieChart>
            </ChartContainer>
            <ul className="min-w-0 flex-1 space-y-1.5">
              {categories.map((entry, index) => (
                <li key={entry.category} className="flex items-center gap-2 text-body-sm">
                  <span
                    className="size-2.5 shrink-0 rounded-full"
                    style={{ background: chartColor(index) }}
                    aria-hidden="true"
                  />
                  <span className="min-w-0 flex-1 truncate text-neutral-700">{entry.category}</span>
                  <span className="shrink-0 tabular-nums font-medium text-neutral-900">
                    {formatINR(entry.amount, { compact: true })}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className="mt-6 border-t border-neutral-100 pt-4">
            <p className="text-caption font-medium text-neutral-600">{t(language, "dashboard.spend.cashflowTitle")}</p>
            <ChartContainer height={140} className="mt-2">
              <BarChart data={cashflow} margin={{ top: 4, right: 4, left: 4, bottom: 0 }}>
                <Tooltip content={<ChartTooltip valueFormatter={(value) => formatINR(value, { compact: true })} />} />
                <XAxis dataKey="label" tickLine={false} axisLine={false} tick={<ChartTick />} />
                <YAxis hide />
                <Bar dataKey="amount" radius={[6, 6, 0, 0]} maxBarSize={48}>
                  {cashflow.map((entry) => (
                    <Cell
                      key={entry.key}
                      fill={
                        entry.key === "surplus"
                          ? "var(--color-success-500)"
                          : entry.key === "income"
                            ? "var(--color-structural-500)"
                            : "var(--color-structural-300)"
                      }
                    />
                  ))}
                </Bar>
              </BarChart>
            </ChartContainer>
            <ul className="mt-3 grid grid-cols-3 gap-2" aria-label={t(language, "dashboard.spend.cashflowTitle")}>
              {cashflow.map((entry) => (
                <li key={entry.key} className="min-w-0 rounded-sm bg-neutral-50 px-2 py-1.5">
                  <span className="flex items-center gap-1.5 text-caption text-neutral-600">
                    <span
                      className="size-2 shrink-0 rounded-full"
                      style={{
                        background:
                          entry.key === "surplus"
                            ? "var(--color-success-500)"
                            : entry.key === "income"
                              ? "var(--color-structural-500)"
                              : "var(--color-structural-300)",
                      }}
                      aria-hidden="true"
                    />
                    <span className="truncate">{entry.label}</span>
                  </span>
                  <span className="mt-0.5 block text-body-sm font-semibold tabular-nums text-neutral-900">
                    {formatINR(entry.amount, { compact: true })}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}

      <div className="mt-4 flex items-center justify-between border-t border-neutral-100 pt-3">
        <span className="text-caption text-neutral-600">{t(language, "dashboard.spend.monthlySurplus")}</span>
        <MoneyText value={monthlySurplus} size="sm" whyThisNumber={t(language, "header.tooltip.audit")} />
      </div>
    </div>
  );
}
