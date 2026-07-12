import { useState } from "react";
import { Bar, BarChart, Cell, Line, LineChart, Tooltip as RechartsTooltip, XAxis, YAxis } from "recharts";
import { Landmark, ShieldCheck, Sparkles } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Avatar, type AvatarState } from "@/components/shared/Avatar";
import { MoneyText } from "@/components/shared/MoneyText";
import { DataState } from "@/components/shared/DataState";
import {
  ChartContainer,
  ChartGrid,
  ChartTick,
  ChartTooltip,
  chartColor,
} from "@/components/shared/ChartTheme";
import { PhoneFrame, type PhoneFrameNavId } from "@/components/shared/PhoneFrame";
import { TrustFooter } from "@/components/shared/TrustFooter";
import { LangToggle, type LanguageCode } from "@/components/shared/LangToggle";
import { SectionHeader } from "@/components/shared/SectionHeader";
import { formatINR } from "@/lib/format";

const AVATAR_STATES: AvatarState[] = [
  "idle",
  "listening",
  "thinking",
  "speaking",
  "celebrating",
  "concerned",
];

const NET_WORTH_TREND = [
  { month: "Feb", value: 842000 },
  { month: "Mar", value: 861500 },
  { month: "Apr", value: 879200 },
  { month: "May", value: 905800 },
  { month: "Jun", value: 921400 },
  { month: "Jul", value: 948600 },
];

const SPEND_BY_CATEGORY = [
  { category: "Groceries", amount: 12400 },
  { category: "Rent", amount: 28000 },
  { category: "Transport", amount: 5200 },
  { category: "Dining", amount: 6800 },
  { category: "Utilities", amount: 3100 },
];

export default function Dev() {
  const [lang, setLang] = useState<LanguageCode>("en");
  const [navId, setNavId] = useState<PhoneFrameNavId>("wealthmitra");

  return (
    <div className="mx-auto max-w-6xl space-y-16 px-6 py-12">
      <SectionHeader
        eyebrow="Dev playground · Task 14"
        title="Shared UI foundation"
        description="Every component below is rendered in every state/variant it supports. This route is the build's visual verification surface and is removed in Task 19 — it is not part of the shipped app."
      />

      {/* ---------------------------------------------------------------- */}
      <section className="space-y-6">
        <SectionHeader title="MoneyText" description="Tabular numerals, size ramp, compact lakh/crore, signed deltas, and the 'why this number' affordance." />

        <Card>
          <CardHeader>
            <CardTitle>Size ramp</CardTitle>
            <CardDescription>Every size below the hero uses IBM Plex Sans; the hero figure alone uses Space Grotesk.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap items-end gap-8">
            <MoneyText value={128450} size="sm" />
            <MoneyText value={128450} size="md" />
            <MoneyText value={128450} size="lg" />
            <MoneyText value={1284500} size="xl" />
            <MoneyText value={9486210} size="hero" compact />
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Deltas — signed, colored, arrowed</CardTitle>
              <CardDescription>Color never carries the signal alone.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <MoneyText value={62400} delta={4200} size="lg" />
              <MoneyText value={18900} delta={-3100} size="lg" />
              <MoneyText value={948600} deltaPercent={2.9} size="lg" compact />
              <MoneyText value={12000} delta={0} size="lg" />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Compact grouping + trust affordance</CardTitle>
              <CardDescription>₹1,23,456 grouping vs ₹L/Cr shorthand, and the info-icon "why this number" tooltip.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <MoneyText value={1234567} size="lg" />
              <MoneyText value={1234567} size="lg" compact />
              <MoneyText
                value={24500}
                size="lg"
                delta={1800}
                whyThisNumber="Computed from 90 days of savings-account credits minus recurring debits (method: surplus_v1)."
              />
            </CardContent>
          </Card>
        </div>
      </section>

      {/* ---------------------------------------------------------------- */}
      <section className="space-y-6">
        <SectionHeader title="Avatar" description="2D companion mascot, six states — pure CSS/SVG + Framer Motion, honors prefers-reduced-motion." />
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {AVATAR_STATES.map((state) => (
            <Card key={state} className="items-center py-6 text-center">
              <CardContent className="flex flex-col items-center gap-3">
                <Avatar state={state} size={72} />
                <span className="text-caption font-medium capitalize text-neutral-600">{state}</span>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* ---------------------------------------------------------------- */}
      <section className="space-y-6">
        <SectionHeader title="DataState" description="The four mandatory states — loading, empty, error, populated — rendered simultaneously." />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Loading</CardTitle>
            </CardHeader>
            <CardContent>
              <DataState status="loading">{null}</DataState>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Empty</CardTitle>
            </CardHeader>
            <CardContent>
              <DataState
                status="empty"
                emptyIcon={Landmark}
                emptyTitle="No AA accounts linked yet"
                emptyDescription="Connect an Account Aggregator to see mutual funds, equity, and insurance held outside IDBI."
                emptyAction={{ label: "Link now", onClick: () => {} }}
              >
                {null}
              </DataState>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Error</CardTitle>
            </CardHeader>
            <CardContent>
              <DataState status="error" onRetry={() => {}}>
                {null}
              </DataState>
            </CardContent>
          </Card>

          <Card className="lg:col-span-1">
            <CardHeader>
              <CardTitle>Populated</CardTitle>
            </CardHeader>
            <CardContent>
              <DataState status="success">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-body-sm text-neutral-600">This month's spend</span>
                    <MoneyText value={55500} delta={-2100} size="md" />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-body-sm text-neutral-600">Idle balance</span>
                    <MoneyText value={214000} size="md" />
                  </div>
                </div>
              </DataState>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* ---------------------------------------------------------------- */}
      <section className="space-y-6">
        <SectionHeader title="ChartTheme" description="Recharts wrapper — token colors (no purple), minimal 1px neutral grid, flat bordered tooltip." />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.4fr_1fr]">
          <Card>
            <CardHeader>
              <CardTitle>Net worth trend</CardTitle>
              <CardDescription>Six-month rolling view, single structural-teal series.</CardDescription>
            </CardHeader>
            <CardContent>
              <ChartContainer height={240}>
                <LineChart data={NET_WORTH_TREND} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <ChartGrid />
                  <XAxis dataKey="month" axisLine={false} tickLine={false} tick={<ChartTick />} />
                  <YAxis
                    axisLine={false}
                    tickLine={false}
                    tick={<ChartTick />}
                    tickFormatter={(value: number) => formatINR(value, { compact: true }).replace("₹", "")}
                    width={48}
                  />
                  <RechartsTooltip
                    content={<ChartTooltip valueFormatter={(value) => formatINR(value, { compact: true })} />}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    name="Net worth"
                    stroke={chartColor(0)}
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ChartContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Spend by category</CardTitle>
              <CardDescription>Categorical series from the structural/brand/semantic ramps.</CardDescription>
            </CardHeader>
            <CardContent>
              <ChartContainer height={240}>
                <BarChart data={SPEND_BY_CATEGORY} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <ChartGrid />
                  <XAxis dataKey="category" axisLine={false} tickLine={false} tick={<ChartTick />} interval={0} />
                  <YAxis
                    axisLine={false}
                    tickLine={false}
                    tick={<ChartTick />}
                    tickFormatter={(value: number) => formatINR(value, { compact: true }).replace("₹", "")}
                    width={40}
                  />
                  <RechartsTooltip
                    content={<ChartTooltip valueFormatter={(value) => formatINR(value, { compact: true })} />}
                  />
                  <Bar dataKey="amount" name="Spend" radius={[4, 4, 0, 0]}>
                    {SPEND_BY_CATEGORY.map((entry, index) => (
                      <Cell key={entry.category} fill={chartColor(index)} />
                    ))}
                  </Bar>
                </BarChart>
              </ChartContainer>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* ---------------------------------------------------------------- */}
      <section className="space-y-6">
        <SectionHeader title="PhoneFrame" description="The IDBI-mobile shell used by /app, /present, and /channels — status bar, header band, scrollable content, bottom nav." />
        <div className="flex flex-wrap items-start gap-8">
          <PhoneFrame activeNav={navId} onNavChange={setNavId}>
            <div className="flex flex-col gap-4 p-4">
              <div className="flex items-center gap-3 rounded-lg border border-neutral-200 bg-neutral-0 p-4">
                <Avatar state="speaking" size={48} />
                <div>
                  <p className="text-body-sm font-semibold text-neutral-800">WealthMitra</p>
                  <p className="text-caption text-neutral-600">"Your idle balance can work harder — want to see how?"</p>
                </div>
              </div>
              <Card size="sm">
                <CardContent>
                  <div className="flex items-center justify-between">
                    <span className="text-body-sm text-neutral-600">Net worth</span>
                    <MoneyText value={948600} delta={26800} size="md" />
                  </div>
                </CardContent>
              </Card>
            </div>
            <TrustFooter />
          </PhoneFrame>

          <div className="max-w-sm space-y-3 text-body-sm text-neutral-600">
            <p>
              Active nav tab: <span className="font-medium text-neutral-900">{navId}</span>. Tap
              any bottom-nav item to see the active state change — WealthMitra stays
              center-highlighted in brand orange regardless of selection.
            </p>
          </div>
        </div>
      </section>

      {/* ---------------------------------------------------------------- */}
      <section className="space-y-6">
        <SectionHeader title="TrustFooter, LangToggle, SectionHeader" description="Standing trust cue, language segmented toggle, and the section-header primitive used throughout this page." />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>LangToggle</CardTitle>
              <CardDescription>Native-script segmented control. Selected: {lang}.</CardDescription>
            </CardHeader>
            <CardContent>
              <LangToggle value={lang} onChange={setLang} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>TrustFooter</CardTitle>
              <CardDescription>Rendered edge-to-edge at the bottom of a data view.</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <TrustFooter />
            </CardContent>
          </Card>
        </div>
      </section>

      {/* ---------------------------------------------------------------- */}
      <section className="space-y-6">
        <SectionHeader
          title="Button touch targets"
          description="shadcn's default sizes (default/sm/lg) render sub-44px. The new 'touch' size variant clears the mobile hit-area minimum."
        />
        <Card>
          <CardContent className="flex flex-wrap items-center gap-4">
            <Button size="default">Default (32px)</Button>
            <Button size="lg">Large (36px)</Button>
            <Button size="touch">Touch (44px)</Button>
            <Button size="icon-touch" variant="outline" aria-label="Trust badge">
              <ShieldCheck size={20} strokeWidth={1.75} />
            </Button>
            <Button size="touch" variant="secondary">
              <Sparkles size={18} strokeWidth={1.75} />
              Ask WealthMitra
            </Button>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
