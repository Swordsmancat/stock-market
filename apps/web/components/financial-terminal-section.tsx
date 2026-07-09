import * as React from "react";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export const financialTerminalCardClassName =
  "overflow-hidden rounded-md border border-border/80 bg-card/95 shadow-[0_0_0_1px_hsl(var(--primary)/0.04)]";

export const financialTerminalHeaderClassName =
  "border-b border-border/70 bg-background/60 p-3 sm:p-4";

export const financialTerminalContentClassName = "p-3 sm:p-4";

export const financialTerminalSurfaceClassName =
  "rounded-md border border-border/70 bg-background/60";

type CardProps = React.ComponentProps<typeof Card>;
type CardHeaderProps = React.ComponentProps<typeof CardHeader>;
type CardContentProps = React.ComponentProps<typeof CardContent>;

export function FinancialTerminalCard({ className, ...props }: CardProps) {
  return (
    <Card
      className={cn(financialTerminalCardClassName, className)}
      {...props}
    />
  );
}

export function FinancialTerminalCardHeader({
  className,
  ...props
}: CardHeaderProps) {
  return (
    <CardHeader
      className={cn(financialTerminalHeaderClassName, className)}
      {...props}
    />
  );
}

export function FinancialTerminalCardContent({
  className,
  ...props
}: CardContentProps) {
  return (
    <CardContent
      className={cn(financialTerminalContentClassName, className)}
      {...props}
    />
  );
}

export function FinancialTerminalSurface({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(financialTerminalSurfaceClassName, className)}
      {...props}
    />
  );
}
