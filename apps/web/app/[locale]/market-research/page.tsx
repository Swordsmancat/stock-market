import { getTranslations } from "next-intl/server";

import {
  EconomicCalendarPanel,
  type EconomicCalendarPayload,
} from "@/components/economic-calendar-panel";
import { ErrorState } from "@/components/error-state";
import { FinancialPageHeader } from "@/components/financial-page-header";
import {
  IndustryRankingHistoryPanel,
  type IndustryRankingPayload,
} from "@/components/industry-ranking-history-panel";
import { Button } from "@/components/ui/button";
import { backendFetch } from "@/lib/backend-api";
import { Link } from "@/src/i18n/routing";

type LoadResult<T> =
  | { status: "loaded"; payload: T }
  | { status: "failed"; payload: null };

function currentShanghaiMonth(): { start: string; end: string } {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
  }).formatToParts(new Date());
  const year = Number(parts.find((part) => part.type === "year")?.value);
  const month = Number(parts.find((part) => part.type === "month")?.value);
  const lastDay = new Date(Date.UTC(year, month, 0)).getUTCDate();
  return {
    start: `${year}-${String(month).padStart(2, "0")}-01`,
    end: `${year}-${String(month).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`,
  };
}

async function fetchEconomicCalendar(): Promise<LoadResult<EconomicCalendarPayload>> {
  const { start, end } = currentShanghaiMonth();
  try {
    const response = await backendFetch(
      `/economic-calendar/events?start=${start}&end=${end}&limit=200`,
      { cache: "no-store" },
    );
    if (!response.ok) return { status: "failed", payload: null };
    return {
      status: "loaded",
      payload: (await response.json()) as EconomicCalendarPayload,
    };
  } catch {
    return { status: "failed", payload: null };
  }
}

async function fetchIndustryRankings(): Promise<LoadResult<IndustryRankingPayload>> {
  try {
    const response = await backendFetch(
      "/sectors/industry-rankings?days=20&limit=20",
      { cache: "no-store" },
    );
    if (!response.ok) return { status: "failed", payload: null };
    return {
      status: "loaded",
      payload: (await response.json()) as IndustryRankingPayload,
    };
  } catch {
    return { status: "failed", payload: null };
  }
}

export default async function MarketResearchPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const [{ locale }, t, calendarT, rankingT, calendarResult, rankingResult] =
    await Promise.all([
      params,
      getTranslations("MarketResearch"),
      getTranslations("EconomicCalendar"),
      getTranslations("IndustryRankingHistory"),
      fetchEconomicCalendar(),
      fetchIndustryRankings(),
    ]);

  return (
    <div className="space-y-6">
      <FinancialPageHeader
        title={t("title")}
        description={t("description")}
        badges={[{ label: t("badge"), variant: "secondary" }]}
        metrics={[
          {
            label: t("calendarMetric"),
            value:
              calendarResult.status === "loaded"
                ? calendarResult.payload.count
                : t("unavailable"),
            description: t("calendarMetricDescription"),
          },
          {
            label: t("rankingMetric"),
            value:
              rankingResult.status === "loaded"
                ? rankingResult.payload.dates.length
                : t("unavailable"),
            description: t("rankingMetricDescription"),
          },
        ]}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" asChild>
              <Link href="/topic-research">{t("openTopicResearch")}</Link>
            </Button>
            <Button size="sm" variant="outline" asChild>
              <Link href="/evidence">{t("openMacroResearch")}</Link>
            </Button>
          </div>
        }
      />

      {calendarResult.status === "loaded" ? (
        <EconomicCalendarPanel
          payload={calendarResult.payload}
          locale={locale}
          labels={{
            title: calendarT("title"),
            description: calendarT("description"),
            refresh: calendarT("refresh"),
            refreshing: calendarT("refreshing"),
            refreshSuccess: calendarT("refreshSuccess", { count: "{count}" }),
            refreshFailed: calendarT("refreshFailed"),
            allCountries: calendarT("allCountries"),
            allImportance: calendarT("allImportance"),
            importance: calendarT("importance"),
            time: calendarT("time"),
            country: calendarT("country"),
            event: calendarT("event"),
            previous: calendarT("previous"),
            forecast: calendarT("forecast"),
            actual: calendarT("actual"),
            empty: calendarT("empty"),
            unavailable: t("unavailable"),
          }}
        />
      ) : (
        <ErrorState
          title={calendarT("loadFailedTitle")}
          description={calendarT("loadFailedDescription")}
        />
      )}

      {rankingResult.status === "loaded" ? (
        <IndustryRankingHistoryPanel
          locale={locale}
          payload={rankingResult.payload}
          labels={{
            title: rankingT("title"),
            description: rankingT("description"),
            refresh: rankingT("refresh"),
            refreshing: rankingT("refreshing"),
            empty: rankingT("empty"),
            rank: rankingT("rank"),
            failed: rankingT("failed"),
            ladderView: rankingT("ladderView"),
            listView: rankingT("listView"),
            type: rankingT("type"),
            industry: rankingT("industry"),
            level: rankingT("level"),
            firstLevel: rankingT("firstLevel"),
            sort: rankingT("sort"),
            gainDesc: rankingT("gainDesc"),
            gainAsc: rankingT("gainAsc"),
            count: rankingT("count"),
            topCount: rankingT("topCount", { count: "{count}" }),
            days: rankingT("days"),
            tradingDays: rankingT("tradingDays", { count: "{count}" }),
            sector: rankingT("sector"),
            change: rankingT("change"),
            code: rankingT("code"),
            source: rankingT("source"),
            updatedAt: rankingT("updatedAt", { time: "{time}" }),
          }}
        />
      ) : (
        <ErrorState
          title={rankingT("loadFailedTitle")}
          description={rankingT("loadFailedDescription")}
        />
      )}
    </div>
  );
}
