import { Building2, Database, ExternalLink, Gem, Newspaper, ShoppingBasket, TrendingUp, Wheat } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { FinancialPageHeader } from "@/components/financial-page-header";
import {
  FinancialTerminalCard,
  FinancialTerminalCardContent,
  FinancialTerminalCardHeader,
  FinancialTerminalSurface,
} from "@/components/financial-terminal-section";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardDescription, CardTitle } from "@/components/ui/card";
import { backendFetch } from "@/lib/backend-api";
import {
  decodeTopicResearchPayload,
  type TopicResearchId,
  type TopicResearchPayload,
  type TopicResearchWindow,
} from "@/lib/topic-research";
import { Link } from "@/src/i18n/routing";

type SearchParams = Record<string, string | string[] | undefined>;

const TOPICS: Array<{ id: TopicResearchId; icon: typeof Wheat }> = [
  { id: "agriculture", icon: Wheat },
  { id: "consumption", icon: ShoppingBasket },
  { id: "real_estate", icon: Building2 },
  { id: "nonferrous", icon: Gem },
];
const WINDOWS: TopicResearchWindow[] = ["30d", "90d", "180d"];

function first(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
}

function normalizeTopic(value: string): TopicResearchId {
  return TOPICS.some((item) => item.id === value) ? (value as TopicResearchId) : "agriculture";
}

function normalizeWindow(value: string): TopicResearchWindow {
  return WINDOWS.includes(value as TopicResearchWindow) ? (value as TopicResearchWindow) : "90d";
}

function topicHref(topic: TopicResearchId, window: TopicResearchWindow): string {
  const params = new URLSearchParams({ topic });
  if (window !== "90d") params.set("window", window);
  return `/topic-research?${params.toString()}`;
}

async function loadTopic(topic: TopicResearchId, window: TopicResearchWindow): Promise<TopicResearchPayload | null> {
  try {
    const response = await backendFetch(`/topic-research?topic=${topic}&window=${window}`, { cache: "no-store" });
    if (!response.ok) return null;
    return decodeTopicResearchPayload(await response.json());
  } catch {
    return null;
  }
}

function formattedNewsTime(value: string, locale: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat(locale === "zh" ? "zh-CN" : "en-US", {
    timeZone: "Asia/Shanghai",
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed);
}

export default async function TopicResearchPage({
  params,
  searchParams = Promise.resolve({}),
}: {
  params: Promise<{ locale: string }>;
  searchParams?: Promise<SearchParams>;
}) {
  const [{ locale }, resolvedSearchParams, t] = await Promise.all([
    params,
    searchParams,
    getTranslations("TopicResearch"),
  ]);
  const selectedTopic = normalizeTopic(first(resolvedSearchParams.topic));
  const selectedWindow = normalizeWindow(first(resolvedSearchParams.window));
  const payload = await loadTopic(selectedTopic, selectedWindow);
  const readySections = payload
    ? Object.values(payload.sections).filter((section) => section.status === "ready").length
    : 0;

  return (
    <div className="space-y-5">
      <FinancialPageHeader
        title={t("title")}
        description={t("description")}
        badges={[
          { label: t("storedOnly"), variant: "secondary" },
          { label: t("researchOnly") },
        ]}
        metrics={[
          { label: t("evidenceCount"), value: payload?.evidenceCount ?? 0 },
          { label: t("latestEvidence"), value: payload?.latestEvidenceDate ?? t("unavailable") },
          { label: t("availableSections"), value: `${readySections}/3` },
          { label: t("currentWindow"), value: t(`window${selectedWindow}`) },
        ]}
        actions={
          <Button variant="outline" size="sm" asChild>
            <Link href="/market-research">{t("backToMarketResearch")}</Link>
          </Button>
        }
      />

      <FinancialTerminalCard>
        <FinancialTerminalCardContent className="space-y-3">
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4" role="group" aria-label={t("topicLabel")}>
            {TOPICS.map(({ id, icon: Icon }) => (
              <Button key={id} variant={id === selectedTopic ? "default" : "outline"} asChild className="justify-start">
                <Link href={topicHref(id, selectedWindow) as any} aria-current={id === selectedTopic ? "page" : undefined}>
                  <Icon className="mr-2 h-4 w-4" />{t(`topic${id}`)}
                </Link>
              </Button>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-2" role="group" aria-label={t("windowLabel")}>
            <span className="text-xs text-muted-foreground">{t("windowLabel")}</span>
            {WINDOWS.map((window) => (
              <Button key={window} size="sm" variant={window === selectedWindow ? "secondary" : "ghost"} asChild>
                <Link href={topicHref(selectedTopic, window) as any} aria-current={window === selectedWindow ? "page" : undefined}>
                  {t(`window${window}`)}
                </Link>
              </Button>
            ))}
          </div>
        </FinancialTerminalCardContent>
      </FinancialTerminalCard>

      {payload === null ? (
        <FinancialTerminalCard>
          <FinancialTerminalCardContent><ErrorState title={t("loadFailed")} description={t("loadFailedDescription")} /></FinancialTerminalCardContent>
        </FinancialTerminalCard>
      ) : (
        <>
          <FinancialTerminalSurface className="flex flex-wrap items-center gap-x-4 gap-y-1 p-3 text-xs text-muted-foreground">
            <Database className="h-4 w-4" />
            <span>{t("coverage", { start: payload.period.start, end: payload.period.end })}</span>
            <span>{t("taxonomy", { version: payload.taxonomyVersion })}</span>
          </FinancialTerminalSurface>

          <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(20rem,0.8fr)]">
            <FinancialTerminalCard>
              <FinancialTerminalCardHeader>
                <CardTitle className="flex items-center gap-2 text-base"><Newspaper className="h-4 w-4" />{t("newsTitle")}</CardTitle>
                <CardDescription>{t("sectionDescription", { count: payload.sections.news.total, date: payload.sections.news.latestDate ?? t("unavailable") })}</CardDescription>
              </FinancialTerminalCardHeader>
              <FinancialTerminalCardContent className="space-y-2">
                {payload.sections.news.status === "empty" ? (
                  <EmptyState title={t("newsEmpty")} description={t("newsEmptyDescription")} />
                ) : payload.sections.news.items.map((item) => (
                  <FinancialTerminalSurface key={item.id} className="p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <a href={item.url} target="_blank" rel="noreferrer" className="font-medium text-foreground hover:text-primary">
                          {item.title}<ExternalLink className="ml-1 inline h-3.5 w-3.5" />
                        </a>
                        {item.summary ? <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{item.summary}</p> : null}
                      </div>
                      <Badge variant="outline" className="shrink-0 font-mono">{item.symbol}</Badge>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
                      <time dateTime={item.publishedAt}>{formattedNewsTime(item.publishedAt, locale)}</time>
                      <span>{item.source}</span>
                      <span>{t("matchedBy", { field: t(`matchField${item.matchedOn.field}`), keyword: item.matchedOn.keyword })}</span>
                    </div>
                  </FinancialTerminalSurface>
                ))}
              </FinancialTerminalCardContent>
            </FinancialTerminalCard>

            <div className="grid min-w-0 content-start gap-4">
              <FinancialTerminalCard>
                <FinancialTerminalCardHeader>
                  <CardTitle className="flex items-center gap-2 text-base"><TrendingUp className="h-4 w-4" />{t("rankingTitle")}</CardTitle>
                  <CardDescription>{t("sectionDescription", { count: payload.sections.industryRankings.total, date: payload.sections.industryRankings.latestDate ?? t("unavailable") })}</CardDescription>
                </FinancialTerminalCardHeader>
                <FinancialTerminalCardContent className="space-y-2">
                  {payload.sections.industryRankings.status === "empty" ? (
                    <EmptyState title={t("rankingEmpty")} description={t("rankingEmptyDescription")} />
                  ) : payload.sections.industryRankings.items.map((item) => (
                    <a key={`${item.date}-${item.code}`} href={item.sourceUrl} target="_blank" rel="noreferrer" className="block">
                      <FinancialTerminalSurface className="grid grid-cols-[5.5rem_minmax(0,1fr)_4.5rem] items-center gap-2 p-2.5 text-sm hover:bg-accent/40">
                        <time dateTime={item.date} className="font-mono text-xs text-muted-foreground">{item.date}</time>
                        <div className="min-w-0"><div className="truncate font-medium">{item.name}</div><div className="text-xs text-muted-foreground">#{item.rank} · {item.provider}</div></div>
                        <span className={`text-right font-mono ${item.changePercent > 0 ? "text-rose-500" : item.changePercent < 0 ? "text-emerald-500" : "text-muted-foreground"}`}>{item.changePercent > 0 ? "+" : ""}{item.changePercent.toFixed(2)}%</span>
                      </FinancialTerminalSurface>
                    </a>
                  ))}
                </FinancialTerminalCardContent>
              </FinancialTerminalCard>

              <FinancialTerminalCard>
                <FinancialTerminalCardHeader>
                  <CardTitle className="flex items-center gap-2 text-base"><Building2 className="h-4 w-4" />{t("companiesTitle")}</CardTitle>
                  <CardDescription>{t("sectionDescription", { count: payload.sections.companies.total, date: payload.sections.companies.latestDate ?? t("unavailable") })}</CardDescription>
                </FinancialTerminalCardHeader>
                <FinancialTerminalCardContent className="space-y-2">
                  {payload.sections.companies.status === "empty" ? (
                    <EmptyState title={t("companiesEmpty")} description={t("companiesEmptyDescription")} />
                  ) : payload.sections.companies.items.map((item) => {
                    const content = (
                      <FinancialTerminalSurface className="p-3 hover:bg-accent/40">
                        <div className="flex items-start justify-between gap-3"><div className="min-w-0"><div className="truncate font-medium">{item.name}</div><div className="text-xs text-muted-foreground">{item.industry ?? t("unavailable")}</div></div><span className="font-mono text-sm">{item.symbol}</span></div>
                        <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">{item.businessScope ?? item.profile ?? t("unavailable")}</p>
                        <div className="mt-2 text-xs text-muted-foreground">{t("companyAsOf", { date: item.asOf })} · {t("matchedBy", { field: t(`matchField${item.matchedOn.field}`), keyword: item.matchedOn.keyword })}</div>
                      </FinancialTerminalSurface>
                    );
                    return item.market ? <Link key={item.symbol} href={`/instruments/${encodeURIComponent(item.symbol)}?market=${encodeURIComponent(item.market)}` as any} className="block">{content}</Link> : <div key={item.symbol}>{content}</div>;
                  })}
                </FinancialTerminalCardContent>
              </FinancialTerminalCard>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
