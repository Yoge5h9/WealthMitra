import type { LucideIcon } from "lucide-react";
import { ArrowUpRight, Construction } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface PlaceholderPageProps {
  eyebrow: string;
  title: string;
  description: string;
  icon: LucideIcon;
  upcoming: string[];
  primaryAction: string;
}

export function PlaceholderPage({
  eyebrow,
  title,
  description,
  icon: Icon,
  upcoming,
  primaryAction,
}: PlaceholderPageProps) {
  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.7fr_1fr]">
        <Card className="lg:py-8">
          <CardHeader className="lg:px-8">
            <span className="text-caption font-medium uppercase tracking-wide text-structural-600">
              {eyebrow}
            </span>
            <h1 className="mt-2 font-display text-h1 font-bold tracking-tight text-neutral-900">
              {title}
            </h1>
            <p className="mt-3 max-w-2xl text-lg text-neutral-600">
              {description}
            </p>
          </CardHeader>
          <CardContent className="lg:px-8">
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <Button size="lg" className="min-h-11 min-w-11">
                {primaryAction}
                <ArrowUpRight size={20} strokeWidth={1.75} />
              </Button>
              <Button variant="outline" size="lg" className="min-h-11 min-w-11">
                View build plan
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2 text-structural-600">
              <Construction size={20} strokeWidth={1.75} />
              <span className="text-caption font-semibold uppercase tracking-wide">
                Build status
              </span>
            </div>
            <CardTitle>
              <span className="font-display text-h4">Scaffolded, not wired</span>
            </CardTitle>
            <CardDescription>
              This surface is a routed placeholder from the frontend skeleton.
              Real data, states, and interactions land in later build tasks.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="mb-3 flex items-center gap-2 text-neutral-500">
              <Icon size={16} strokeWidth={1.75} />
              <span className="text-caption">What will live here</span>
            </div>
            <ul className="space-y-2">
              {upcoming.map((item) => (
                <li
                  key={item}
                  className="flex items-start gap-2 text-body-sm text-neutral-700"
                >
                  <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-brand-500" />
                  {item}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
