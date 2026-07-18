import { getTranslations } from "next-intl/server";

import { FinancialPageHeader } from "@/components/financial-page-header";
import { InvestmentCalendar } from "@/components/investment-calendar";
import { backendFetch } from "@/lib/backend-api";
import {
  isInvestmentCalendarPayload,
  parseInvestmentCalendarQuery,
  type InvestmentCalendarPayload,
} from "@/lib/investment-calendar";

type SearchValue = string | string[] | undefined;
type LoadResult =
  | { status: "loaded"; payload: InvestmentCalendarPayload }
  | { status: "failed"; payload: null };

async function loadCalendar(path: string): Promise<LoadResult> {
  try {
    const response = await backendFetch(path, { cache: "no-store" });
    if (!response.ok) return { status: "failed", payload: null };
    const payload: unknown = await response.json();
    return isInvestmentCalendarPayload(payload)
      ? { status: "loaded", payload }
      : { status: "failed", payload: null };
  } catch {
    return { status: "failed", payload: null };
  }
}

export default async function InvestmentCalendarPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  const [{ locale }, resolvedSearchParams, t] = await Promise.all([
    params,
    searchParams,
    getTranslations("InvestmentCalendar"),
  ]);
  const query = parseInvestmentCalendarQuery(resolvedSearchParams);
  const apiQuery = new URLSearchParams({
    start: query.start,
    end: query.end,
    kind: query.kind,
    min_importance: String(query.importance),
  });
  const result = await loadCalendar(`/investment-calendar?${apiQuery.toString()}`);
  const payload = result.status === "loaded" ? result.payload : null;
  const highestImportance = payload?.days.reduce(
    (highest, day) => Math.max(highest, day.max_importance ?? 0),
    0,
  );

  return (
    <div className="space-y-4">
      <FinancialPageHeader
        title={t("title")}
        description={t("description")}
        badges={[
          { label: t("personalResearch"), variant: "secondary" },
          { label: t("readOnly"), variant: "outline" },
        ]}
        metrics={[
          {
            label: t("metricEvents"),
            value: payload?.count ?? t("unavailable"),
            description: t("metricEventsDescription"),
          },
          {
            label: t("metricActiveDays"),
            value: payload?.days.length ?? t("unavailable"),
            description: t("metricActiveDaysDescription"),
          },
          {
            label: t("metricHighestImportance"),
            value:
              query.kind === "company"
                ? t("notRated")
                : highestImportance
                  ? t("importanceScore", { score: highestImportance })
                  : t("unavailable"),
            description: t("metricHighestImportanceDescription"),
          },
        ]}
      />

      <InvestmentCalendar
        locale={locale}
        query={query}
        payload={payload}
        labels={{
          economic: t("economic"),
          company: t("company"),
          previousMonth: t("previousMonth"),
          nextMonth: t("nextMonth"),
          today: t("today"),
          importance: t("importance"),
          allImportance: t("allImportance"),
          importanceAtLeast: t("importanceAtLeast", { score: "{score}" }),
          importanceScore: t("importanceScore", { score: "{score}" }),
          eventCount: t("eventCount", { count: "{count}" }),
          selectedDayCount: t("selectedDayCount", { count: "{count}" }),
          emptyMonth: t("emptyMonth"),
          emptyDay: t("emptyDay"),
          loadFailedTitle: t("loadFailedTitle"),
          loadFailedDescription: t("loadFailedDescription"),
          truncated: t("truncated"),
          previous: t("previous"),
          forecast: t("forecast"),
          actual: t("actual"),
          referencePeriod: t("referencePeriod"),
          category: t("category"),
          source: t("source"),
          retrievedAt: t("retrievedAt"),
          databaseOnly: t("databaseOnly"),
          unavailable: t("unavailable"),
          weekdays: [
            t("weekdayMonday"),
            t("weekdayTuesday"),
            t("weekdayWednesday"),
            t("weekdayThursday"),
            t("weekdayFriday"),
            t("weekdaySaturday"),
            t("weekdaySunday"),
          ],
        }}
      />
    </div>
  );
}
