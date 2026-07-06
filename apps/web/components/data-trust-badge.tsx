import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { getDataTrustTitle, type DataTrustSignal } from "@/lib/data-trust";

type DataTrustBadgeProps = {
  signal: DataTrustSignal;
  mode?: "compact" | "summary";
  className?: string;
};

const BADGE_CLASS_BY_SEVERITY: Record<DataTrustSignal["severity"], string> = {
  ok: "border-slate-300 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200",
  fresh: "border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
  delayed: "border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200",
  stale: "border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200",
  mock: "border-purple-300 bg-purple-50 text-purple-800 dark:border-purple-800 dark:bg-purple-950 dark:text-purple-200",
  degraded: "border-orange-300 bg-orange-50 text-orange-800 dark:border-orange-800 dark:bg-orange-950 dark:text-orange-200",
  no_data: "border-slate-300 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200",
  unavailable: "border-red-300 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200",
  unknown: "border-muted-foreground/30 bg-muted text-muted-foreground",
};

function buildVisibleDetails(signal: DataTrustSignal): string[] {
  const visibleDetails: string[] = [];
  if (signal.effectiveProvider || signal.provider) {
    visibleDetails.push(`provider: ${signal.effectiveProvider ?? signal.provider}`);
  }
  if (signal.source) {
    visibleDetails.push(`source: ${signal.source}`);
  }
  if (signal.asOf) {
    visibleDetails.push(`as_of: ${signal.asOf}`);
  }
  if (signal.generatedAt) {
    visibleDetails.push(`generated_at: ${signal.generatedAt}`);
  }
  if (signal.isDelayed === true) {
    visibleDetails.push(signal.delayMinutes ? `delay: ${signal.delayMinutes}m` : "delay: declared");
  } else if (signal.isRealtime === true) {
    visibleDetails.push("realtime: declared");
  }
  if (signal.cacheStatus) {
    visibleDetails.push(`cache: ${signal.cacheStatus}`);
  }
  if (signal.sessionStatus) {
    visibleDetails.push(`session: ${signal.sessionStatus}`);
  }
  if (signal.reason) {
    visibleDetails.push(signal.reason);
  }
  return visibleDetails;
}

export function DataTrustBadge({ signal, mode = "compact", className }: DataTrustBadgeProps) {
  const title = getDataTrustTitle(signal);
  const visibleDetails = buildVisibleDetails(signal);

  if (mode === "summary") {
    return (
      <div className={cn("flex flex-col gap-1 text-xs", className)} title={title} aria-label={title}>
        <Badge variant="outline" className={cn("w-fit", BADGE_CLASS_BY_SEVERITY[signal.severity])}>
          {signal.label}
        </Badge>
        {visibleDetails.length > 0 ? (
          <div className="space-y-0.5 text-muted-foreground">
            {visibleDetails.map((detail) => (
              <div key={detail}>{detail}</div>
            ))}
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <Badge
      variant="outline"
      className={cn(BADGE_CLASS_BY_SEVERITY[signal.severity], className)}
      title={title}
      aria-label={title}
    >
      {signal.label}
    </Badge>
  );
}
