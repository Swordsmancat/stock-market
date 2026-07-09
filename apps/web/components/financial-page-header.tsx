import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export type FinancialPageHeaderBadge = {
  label: string;
  variant?: "default" | "secondary" | "destructive" | "outline";
};

export type FinancialPageHeaderMetric = {
  label: string;
  value: ReactNode;
  description?: ReactNode;
  className?: string;
};

type FinancialPageHeaderProps = {
  title: string;
  description: ReactNode;
  badges: FinancialPageHeaderBadge[];
  metrics: FinancialPageHeaderMetric[];
  actions?: ReactNode;
  warningPanel?: ReactNode;
};

export function FinancialPageHeader({
  title,
  description,
  badges,
  metrics,
  actions,
  warningPanel,
}: FinancialPageHeaderProps) {
  return (
    <Card className="overflow-hidden border-primary/15 bg-card shadow-sm">
      <div className="border-b bg-background/95 p-3 sm:p-4">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              {badges.map((badge) => (
                <Badge key={badge.label} variant={badge.variant ?? "outline"} className="rounded-sm px-2 py-0.5 text-[11px]">
                  {badge.label}
                </Badge>
              ))}
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-normal sm:text-2xl">{title}</h1>
              <div className="mt-1 max-w-4xl text-sm leading-6 text-muted-foreground">{description}</div>
            </div>
          </div>
          {actions ? <div className="flex flex-col gap-2 sm:flex-row xl:justify-end">{actions}</div> : null}
        </div>
      </div>
      <CardContent className="p-0">
        <div className="grid divide-y bg-muted/10 sm:grid-cols-2 sm:divide-x sm:divide-y-0 xl:grid-cols-[repeat(auto-fit,minmax(10rem,1fr))]">
          {metrics.map((metric) => (
            <div key={metric.label} className="min-w-0 space-y-1 p-3">
              <div className="text-[11px] font-medium uppercase text-muted-foreground">{metric.label}</div>
              <div className={cn("truncate font-mono text-xl font-semibold tabular-nums sm:text-2xl", metric.className)}>
                {metric.value}
              </div>
              {metric.description ? <div className="truncate text-xs text-muted-foreground">{metric.description}</div> : null}
            </div>
          ))}
        </div>
        {warningPanel ? <div className="border-t p-4">{warningPanel}</div> : null}
      </CardContent>
    </Card>
  );
}
