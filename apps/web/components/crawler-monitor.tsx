import type { LucideIcon } from "lucide-react";
import {
  Activity,
  CircleAlert,
  CircleCheck,
  CircleHelp,
  CircleX,
  Clock3,
  LoaderCircle,
} from "lucide-react";

import { Link } from "@/src/i18n/routing";
import {
  FinancialTerminalCard,
  FinancialTerminalCardContent,
  FinancialTerminalCardHeader,
  FinancialTerminalSurface,
} from "@/components/financial-terminal-section";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardDescription, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  formatCrawlerDuration,
  type CrawlerMonitorItem,
  type CrawlerMonitorPayload,
  type CrawlerPipelineId,
  type CrawlerStatus,
} from "@/lib/crawler-monitor";

type Labels = {
  systemStatus: string;
  detailsTitle: string;
  detailsDescription: string;
  columnPipeline: string;
  columnStatus: string;
  columnScope: string;
  columnSchedule: string;
  columnLatestRun: string;
  columnProgress: string;
  columnFailures: string;
  viewTaskRun: string;
  unavailable: string;
  noProgress: string;
  recentFailures: string;
  pipeline: Record<CrawlerPipelineId, string>;
  scope: Record<CrawlerPipelineId, string>;
  status: Record<CrawlerStatus, string>;
  cadence: Record<string, string>;
  phase: Record<string, string>;
};

const STATUS_PRESENTATION: Record<
  CrawlerStatus,
  { icon: LucideIcon; className: string; badge: "default" | "secondary" | "destructive" | "outline" }
> = {
  running: { icon: LoaderCircle, className: "text-sky-500", badge: "secondary" },
  healthy: { icon: CircleCheck, className: "text-emerald-500", badge: "default" },
  overdue: { icon: Clock3, className: "text-amber-500", badge: "outline" },
  stalled: { icon: CircleAlert, className: "text-orange-500", badge: "outline" },
  failed: { icon: CircleX, className: "text-destructive", badge: "destructive" },
  not_recorded: { icon: CircleHelp, className: "text-muted-foreground", badge: "secondary" },
};

function formatTimestamp(value: string | null, locale: string, fallback: string): string {
  if (!value) return fallback;
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return fallback;
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Shanghai",
  }).format(date);
}

function StatusLabel({ item, labels }: { item: CrawlerMonitorItem; labels: Labels }) {
  const presentation = STATUS_PRESENTATION[item.status];
  const Icon = presentation.icon;
  return (
    <Badge variant={presentation.badge} className="gap-1.5 whitespace-nowrap">
      <Icon
        aria-hidden="true"
        className={`h-3.5 w-3.5 ${presentation.className} ${item.status === "running" ? "animate-spin" : ""}`}
      />
      {labels.status[item.status]}
    </Badge>
  );
}

function ProgressSummary({ item, labels }: { item: CrawlerMonitorItem; labels: Labels }) {
  if (!item.progress) return <span className="text-muted-foreground">{labels.noProgress}</span>;
  const percentage = item.progress.total > 0
    ? Math.min(100, (item.progress.current / item.progress.total) * 100)
    : 0;
  return (
    <div className="min-w-[150px] space-y-1.5">
      <div className="flex items-center justify-between gap-3 text-xs">
        <span className="max-w-[120px] truncate text-muted-foreground">
          {(item.progress.phase && labels.phase[item.progress.phase]) ?? item.progress.phase ?? labels.noProgress}
        </span>
        <span className="font-mono tabular-nums">
          {item.progress.current}/{item.progress.total}
        </span>
      </div>
      <div
        role="progressbar"
        aria-label={`${item.progress.current}/${item.progress.total}`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(percentage)}
        className="h-1.5 overflow-hidden rounded-full bg-secondary"
      >
        <div className="h-full bg-primary transition-[width]" style={{ width: `${percentage}%` }} />
      </div>
    </div>
  );
}

export function CrawlerMonitor({
  payload,
  locale,
  labels,
}: {
  payload: CrawlerMonitorPayload;
  locale: string;
  labels: Labels;
}) {
  return (
    <div className="space-y-4">
      <section aria-labelledby="crawler-status-heading">
        <FinancialTerminalSurface className="p-3 sm:p-4">
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
            <h2 id="crawler-status-heading" className="flex items-center gap-2 text-sm font-semibold">
              <Activity aria-hidden="true" className="h-4 w-4 text-primary" />
              {labels.systemStatus}
            </h2>
            {payload.items.map((item) => {
              const presentation = STATUS_PRESENTATION[item.status];
              const Icon = presentation.icon;
              return (
                <div key={item.id} className="flex min-w-0 items-center gap-1.5 text-sm">
                  <Icon
                    aria-hidden="true"
                    className={`h-3.5 w-3.5 shrink-0 ${presentation.className} ${item.status === "running" ? "animate-spin" : ""}`}
                  />
                  <span className="truncate">{labels.pipeline[item.id]}</span>
                  <span className="text-xs text-muted-foreground">{labels.status[item.status]}</span>
                </div>
              );
            })}
          </div>
        </FinancialTerminalSurface>
      </section>

      <FinancialTerminalCard>
        <FinancialTerminalCardHeader>
          <CardTitle id="crawler-details-heading">{labels.detailsTitle}</CardTitle>
          <CardDescription>{labels.detailsDescription}</CardDescription>
        </FinancialTerminalCardHeader>
        <FinancialTerminalCardContent className="p-0">
          <div className="hidden md:block">
            <Table
              className="min-w-[980px]"
              containerProps={{
                role: "region",
                "aria-labelledby": "crawler-details-heading",
                tabIndex: 0,
              }}
              containerClassName="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              <TableHeader>
                <TableRow>
                  <TableHead>{labels.columnPipeline}</TableHead>
                  <TableHead>{labels.columnStatus}</TableHead>
                  <TableHead>{labels.columnScope}</TableHead>
                  <TableHead>{labels.columnSchedule}</TableHead>
                  <TableHead>{labels.columnLatestRun}</TableHead>
                  <TableHead>{labels.columnProgress}</TableHead>
                  <TableHead>{labels.columnFailures}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {payload.items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>
                      <div className="font-medium">{labels.pipeline[item.id]}</div>
                      <div className="max-w-[230px] truncate font-mono text-[11px] text-muted-foreground">
                        {item.task_name}
                      </div>
                    </TableCell>
                    <TableCell><StatusLabel item={item} labels={labels} /></TableCell>
                    <TableCell>
                      <div>{labels.scope[item.id]}</div>
                      <div className="text-xs text-muted-foreground">{item.provider}</div>
                    </TableCell>
                    <TableCell>{labels.cadence[item.cadence] ?? item.cadence}</TableCell>
                    <TableCell>
                      <div>{formatTimestamp(item.finished_at ?? item.started_at, locale, labels.unavailable)}</div>
                      <div className="text-xs text-muted-foreground">
                        {formatCrawlerDuration(item.duration_ms, locale) ?? labels.unavailable}
                      </div>
                    </TableCell>
                    <TableCell><ProgressSummary item={item} labels={labels} /></TableCell>
                    <TableCell>
                      <div className="font-mono tabular-nums">{item.recent_failure_count}</div>
                      {item.latest_task_run_id ? (
                        <Button asChild variant="link" size="sm" className="h-auto px-0 text-xs">
                          <Link href={`/task-runs/${item.latest_task_run_id}` as any}>{labels.viewTaskRun}</Link>
                        </Button>
                      ) : null}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <div className="divide-y md:hidden">
            {payload.items.map((item) => (
              <article key={item.id} className="space-y-3 p-4">
                <div className="flex min-w-0 items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="truncate text-sm font-medium">{labels.pipeline[item.id]}</h3>
                    <p className="truncate text-xs text-muted-foreground">{labels.scope[item.id]} · {item.provider}</p>
                  </div>
                  <StatusLabel item={item} labels={labels} />
                </div>
                <ProgressSummary item={item} labels={labels} />
                <div className="flex items-end justify-between gap-3 text-xs text-muted-foreground">
                  <div>
                    <div>{labels.cadence[item.cadence] ?? item.cadence}</div>
                    <div>{formatTimestamp(item.finished_at ?? item.started_at, locale, labels.unavailable)}</div>
                  </div>
                  {item.latest_task_run_id ? (
                    <Link href={`/task-runs/${item.latest_task_run_id}` as any} className="text-primary hover:underline">
                      {labels.viewTaskRun}
                    </Link>
                  ) : (
                    <span>{labels.recentFailures}: {item.recent_failure_count}</span>
                  )}
                </div>
              </article>
            ))}
          </div>
        </FinancialTerminalCardContent>
      </FinancialTerminalCard>
    </div>
  );
}
