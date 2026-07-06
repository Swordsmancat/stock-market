import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export type FinancialDashboardHeroBadge = {
  label: string;
  variant?: "default" | "secondary" | "destructive" | "outline";
};

export type FinancialDashboardHeroMetric = {
  label: string;
  value: string;
  description?: string;
  className?: string;
};

type FinancialDashboardHeroProps = {
  title: string;
  description: string;
  badges: FinancialDashboardHeroBadge[];
  metrics: FinancialDashboardHeroMetric[];
  actions?: ReactNode;
  warningPanel?: ReactNode;
};

export function FinancialDashboardHero({
  title,
  description,
  badges,
  metrics,
  actions,
  warningPanel,
}: FinancialDashboardHeroProps) {
  return (
    <Card className="overflow-hidden border-primary/20 bg-gradient-to-br from-background via-muted/20 to-primary/5 shadow-sm">
      <CardHeader className="gap-4 border-b bg-background/70 p-4 backdrop-blur sm:p-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              {badges.map((badge) => (
                <Badge key={badge.label} variant={badge.variant ?? "outline"} className="rounded-sm px-2 py-0.5 text-[11px]">
                  {badge.label}
                </Badge>
              ))}
            </div>
            <div>
              <CardTitle className="text-3xl font-semibold tracking-tight sm:text-4xl">{title}</CardTitle>
              <CardDescription className="mt-2 max-w-3xl text-sm leading-6">{description}</CardDescription>
            </div>
          </div>
          {actions ? <div className="flex flex-col gap-2 sm:flex-row xl:justify-end">{actions}</div> : null}
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="grid divide-y border-b bg-background/60 sm:grid-cols-2 sm:divide-x sm:divide-y-0 xl:grid-cols-4">
          {metrics.map((metric) => (
            <div key={metric.label} className="space-y-1 p-4">
              <div className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">{metric.label}</div>
              <div className={cn("font-mono text-2xl font-semibold tabular-nums", metric.className)}>{metric.value}</div>
              {metric.description ? <div className="text-xs text-muted-foreground">{metric.description}</div> : null}
            </div>
          ))}
        </div>
        {warningPanel ? <div className="p-4">{warningPanel}</div> : null}
      </CardContent>
    </Card>
  );
}
