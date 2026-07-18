import { getTranslations } from "next-intl/server";

import { CrawlerMonitor } from "@/components/crawler-monitor";
import { CrawlerMonitorRefresh } from "@/components/crawler-monitor-refresh";
import { ErrorState } from "@/components/error-state";
import { FinancialPageHeader } from "@/components/financial-page-header";
import { backendFetch } from "@/lib/backend-api";
import {
  isCrawlerMonitorPayload,
  type CrawlerMonitorPayload,
  type CrawlerPipelineId,
  type CrawlerStatus,
} from "@/lib/crawler-monitor";

type LoadResult =
  | { status: "loaded"; payload: CrawlerMonitorPayload }
  | { status: "failed"; payload: null };

async function loadCrawlerMonitor(): Promise<LoadResult> {
  try {
    const response = await backendFetch("/crawler-monitor", { cache: "no-store" });
    if (!response.ok) return { status: "failed", payload: null };
    const payload: unknown = await response.json();
    return isCrawlerMonitorPayload(payload)
      ? { status: "loaded", payload }
      : { status: "failed", payload: null };
  } catch {
    return { status: "failed", payload: null };
  }
}

export default async function CrawlerMonitorPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const [{ locale }, t, result] = await Promise.all([
    params,
    getTranslations("CrawlerMonitor"),
    loadCrawlerMonitor(),
  ]);

  if (result.status === "failed") {
    return (
      <div className="space-y-6">
        <FinancialPageHeader
          title={t("title")}
          description={t("description")}
          badges={[{ label: t("readOnlyBadge"), variant: "secondary" }]}
          metrics={[]}
        />
        <ErrorState title={t("loadFailedTitle")} description={t("loadFailedDescription")} />
      </div>
    );
  }

  const { payload } = result;
  const pipelineIds: CrawlerPipelineId[] = [
    "market_cn",
    "market_us",
    "market_hk",
    "universe_cn",
    "fund_index_cn",
    "evidence_incremental",
    "fundamental_shard",
    "official_disclosures",
    "eastmoney_calendar",
    "eastmoney_industry",
    "eastmoney_news",
    "eastmoney_fundamentals",
  ];
  const statuses: CrawlerStatus[] = [
    "running",
    "healthy",
    "overdue",
    "stalled",
    "failed",
    "not_recorded",
  ];

  return (
    <div className="space-y-6">
      <FinancialPageHeader
        title={t("title")}
        description={t("description")}
        badges={[{ label: t("readOnlyBadge"), variant: "secondary" }]}
        metrics={[
          { label: t("metricTotal"), value: payload.summary.total },
          { label: t("metricRunning"), value: payload.summary.running },
          { label: t("metricHealthy"), value: payload.summary.healthy },
          {
            label: t("metricAttention"),
            value: payload.summary.attention,
            className: payload.summary.attention > 0 ? "text-amber-500" : undefined,
          },
        ]}
        actions={<CrawlerMonitorRefresh label={t("refresh")} />}
      />
      <CrawlerMonitor
        payload={payload}
        locale={locale}
        labels={{
          systemStatus: t("systemStatus"),
          detailsTitle: t("detailsTitle"),
          detailsDescription: t("detailsDescription"),
          columnPipeline: t("columnPipeline"),
          columnStatus: t("columnStatus"),
          columnScope: t("columnScope"),
          columnSchedule: t("columnSchedule"),
          columnLatestRun: t("columnLatestRun"),
          columnProgress: t("columnProgress"),
          columnFailures: t("columnFailures"),
          viewTaskRun: t("viewTaskRun"),
          unavailable: t("unavailable"),
          noProgress: t("noProgress"),
          recentFailures: t("recentFailures"),
          pipeline: Object.fromEntries(
            pipelineIds.map((id) => [id, t(`pipeline_${id}`)]),
          ) as Record<CrawlerPipelineId, string>,
          scope: Object.fromEntries(
            pipelineIds.map((id) => [id, t(`scope_${id}`)]),
          ) as Record<CrawlerPipelineId, string>,
          status: Object.fromEntries(
            statuses.map((status) => [status, t(`status_${status}`)]),
          ) as Record<CrawlerStatus, string>,
          cadence: {
            daily: t("cadence_daily"),
            weekdays: t("cadence_weekdays"),
            hourly: t("cadence_hourly"),
          },
          phase: {
            completed: t("phase_completed"),
            preparing: t("phase_preparing"),
            bars: t("phase_bars"),
            fundamentals: t("phase_fundamentals"),
            metadata: t("phase_metadata"),
            documents: t("phase_documents"),
            persisted: t("phase_persisted"),
            news: t("phase_news"),
          },
        }}
      />
    </div>
  );
}
