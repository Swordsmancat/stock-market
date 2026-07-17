import { getTranslations } from "next-intl/server";
import type { ReactNode } from "react";
import {
  Database,
  ExternalLink,
  FileCheck2,
  FileWarning,
  ListChecks,
  RefreshCw,
  SearchCheck,
  ShieldCheck,
  TerminalSquare,
} from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { EconomicCalendarPanel, type EconomicCalendarPayload } from "@/components/economic-calendar-panel";
import { IndustryRankingHistoryPanel, type IndustryRankingPayload } from "@/components/industry-ranking-history-panel";
import {
  EvidenceSeedImportReview,
  type EvidenceSeedImportReviewLabels,
} from "@/components/evidence-seed-import-review";
import { ErrorState } from "@/components/error-state";
import { FinancialPageHeader } from "@/components/financial-page-header";
import {
  MacroEconomicDashboard,
  type MacroDashboardPayload,
  type MacroEconomicDashboardLabels,
} from "@/components/macro-economic-dashboard";
import {
  FinancialTerminalCard,
  FinancialTerminalCardContent,
  FinancialTerminalCardHeader,
  FinancialTerminalSurface,
} from "@/components/financial-terminal-section";
import {
  OfficialMacroRefreshActions,
  type OfficialMacroRefreshActionsLabels,
} from "@/components/official-macro-refresh-actions";
import {
  OfficialDisclosureEvidencePanel,
  type OfficialDisclosureEvidenceLabels,
  type OfficialDisclosureEvidencePayload,
} from "@/components/official-disclosure-evidence-panel";
import {
  MarketDailyEvidencePanel,
  type MarketDailyEvidencePanelLabels,
  type MarketDailyEvidencePayload,
} from "@/components/market-daily-evidence-panel";
import {
  ResearchSourceNotebook,
  type ResearchSourceNotebookLabels,
  type ResearchSourceNote,
  type ResearchSourceTargetOption,
} from "@/components/research-source-notebook";
import {
  ResearchBriefInbox,
  type ResearchBriefInboxLabels,
  type ResearchBriefPayload,
} from "@/components/research-brief-inbox";
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
import { backendFetch } from "@/lib/backend-api";
import { withProviderQuery } from "@/lib/market-data";
import {
  BUILT_IN_MACRO_LABEL_KEYS,
} from "@/lib/macro-indicator-labels";
import {
  type DashboardBriefPayload,
  type InformationSourceItem,
  type InformationSourcesPayload,
  type MarketOverviewIndicatorItem,
  type MarketOverviewPayload,
  type OfficialMacroSourceStatusPayload,
  type OfficialMacroSourceStatusProvider,
  type ResearchFollowUpQueueItem,
  type ResearchFollowUpQueuePayload,
} from "@/lib/market-overview-payload";
import { getPlatformSettings } from "@/lib/platform-settings-store";
import { Link } from "@/src/i18n/routing";

type EvidenceCenterPageProps = {
  params?: Promise<{ locale: string }>;
  searchParams?: Promise<{ provider?: string }>;
};

type MarketOverviewLoadResult =
  { status: "loaded"; payload: MarketOverviewPayload } | { status: "failed" };

type MacroDashboardLoadResult =
  | { status: "loaded"; payload: MacroDashboardPayload }
  | { status: "failed"; payload: null };

type EconomicCalendarLoadResult =
  | { status: "loaded"; payload: EconomicCalendarPayload }
  | { status: "failed"; payload: null };
type IndustryRankingLoadResult = { status: "loaded"; payload: IndustryRankingPayload } | { status: "failed"; payload: null };

type ResearchSourceNotesLoadResult =
  | { status: "loaded"; items: ResearchSourceNote[] }
  | { status: "failed"; items: [] };

type ResearchBriefsLoadResult =
  | { status: "loaded"; items: ResearchBriefPayload[] }
  | { status: "failed"; items: [] };

type MarketDailyEvidenceLoadResult =
  | { status: "loaded"; payload: MarketDailyEvidencePayload }
  | { status: "failed"; payload: null };

type OfficialMacroSourceStatusLoadResult =
  | { status: "loaded"; payload: OfficialMacroSourceStatusPayload }
  | { status: "failed"; payload: null };

type OfficialDisclosureEvidenceLoadResult =
  | { status: "loaded"; payload: OfficialDisclosureEvidencePayload }
  | { status: "failed"; payload: null };

type IndicatorEvidenceState =
  | "ai_citable"
  | "needs_adapter"
  | "needs_manual_seed"
  | "no_local_evidence"
  | "future"
  | "needs_review";

const FALLBACK_LOCALE = "en-US";
const AUDIT_SOURCE_COMPONENT_KEYS = [
  "source_url",
  "source_series_id",
  "source_document",
  "source_name",
];
const AUDIT_METHOD_COMPONENT_KEYS = [
  "methodology",
  "calculation",
  "notes",
  "review_note",
];
const FRED_OFFICIAL_REFRESH_CODES = [
  "us_10y_yield",
  "us_2y_yield",
  "us_10y_2y_spread",
  "us_cpi_yoy",
  "us_m2_yoy",
];
const WORLD_BANK_BUFFETT_REFRESH_CODES = [
  "buffett_indicator_us",
  "buffett_indicator_cn",
  "buffett_indicator_hk",
];
const FRED_OFFICIAL_SOURCE_IDS = new Set([
  "fred_us_rates",
  "fred_us_inflation",
  "fred_us_liquidity",
]);
const WORLD_BANK_OFFICIAL_SOURCE_IDS = new Set([
  "world_bank_buffett_indicator",
]);

async function fetchMarketOverview(
  provider: string,
): Promise<MarketOverviewLoadResult> {
  try {
    const response = await backendFetch(
      withProviderQuery("/dashboard/market-overview", provider),
      {
        cache: "no-store",
      },
    );
    if (!response.ok) {
      return { status: "failed" };
    }

    return {
      status: "loaded",
      payload: (await response.json()) as MarketOverviewPayload,
    };
  } catch {
    return { status: "failed" };
  }
}

async function fetchMacroDashboard(): Promise<MacroDashboardLoadResult> {
  try {
    const response = await backendFetch(
      "/market-indicators/dashboard?history_limit=12",
      { cache: "no-store" },
    );
    if (!response.ok) return { status: "failed", payload: null };
    return {
      status: "loaded",
      payload: (await response.json()) as MacroDashboardPayload,
    };
  } catch {
    return { status: "failed", payload: null };
  }
}

function currentShanghaiMonth(): { start: string; end: string } {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit" }).formatToParts(new Date());
  const year = Number(parts.find((part) => part.type === "year")?.value);
  const month = Number(parts.find((part) => part.type === "month")?.value);
  const start = `${year}-${String(month).padStart(2, "0")}-01`;
  const end = `${year}-${String(month).padStart(2, "0")}-${String(new Date(Date.UTC(year, month, 0)).getUTCDate()).padStart(2, "0")}`;
  return { start, end };
}

async function fetchEconomicCalendar(): Promise<EconomicCalendarLoadResult> {
  const { start, end } = currentShanghaiMonth();
  try {
    const response = await backendFetch(`/economic-calendar/events?start=${start}&end=${end}&limit=200`, { cache: "no-store" });
    if (!response.ok) return { status: "failed", payload: null };
    return { status: "loaded", payload: await response.json() as EconomicCalendarPayload };
  } catch { return { status: "failed", payload: null }; }
}

async function fetchIndustryRankings(): Promise<IndustryRankingLoadResult> {
  try {
    const response = await backendFetch("/sectors/industry-rankings?days=12&limit=20", { cache: "no-store" });
    if (!response.ok) return { status: "failed", payload: null };
    return { status: "loaded", payload: await response.json() as IndustryRankingPayload };
  } catch { return { status: "failed", payload: null }; }
}

async function fetchOfficialMacroSourceStatus(): Promise<OfficialMacroSourceStatusLoadResult> {
  try {
    const response = await backendFetch(
      "/market-indicators/official-sources/status",
      {
        cache: "no-store",
      },
    );
    if (!response.ok) {
      return { status: "failed", payload: null };
    }

    return {
      status: "loaded",
      payload: (await response.json()) as OfficialMacroSourceStatusPayload,
    };
  } catch {
    return { status: "failed", payload: null };
  }
}

async function fetchResearchSourceNotes(): Promise<ResearchSourceNotesLoadResult> {
  try {
    const response = await backendFetch("/research-source-notes?limit=50", {
      cache: "no-store",
    });
    if (!response.ok) {
      return { status: "failed", items: [] };
    }

    const payload = (await response.json()) as { items?: ResearchSourceNote[] };
    return {
      status: "loaded",
      items: payload.items ?? [],
    };
  } catch {
    return { status: "failed", items: [] };
  }
}

async function fetchResearchBriefs(): Promise<ResearchBriefsLoadResult> {
  try {
    const response = await backendFetch("/research-briefs?limit=10", {
      cache: "no-store",
    });
    if (!response.ok) {
      return { status: "failed", items: [] };
    }

    const payload = (await response.json()) as {
      items?: ResearchBriefPayload[];
    };
    return {
      status: "loaded",
      items: payload.items ?? [],
    };
  } catch {
    return { status: "failed", items: [] };
  }
}

async function fetchMarketDailyEvidence(): Promise<MarketDailyEvidenceLoadResult> {
  try {
    const response = await backendFetch(
      "/market-daily-evidence?limit=12&citable_only=true",
      { cache: "no-store" },
    );
    if (!response.ok) {
      return { status: "failed", payload: null };
    }
    return {
      status: "loaded",
      payload: (await response.json()) as MarketDailyEvidencePayload,
    };
  } catch {
    return { status: "failed", payload: null };
  }
}

async function fetchOfficialDisclosureEvidence(): Promise<OfficialDisclosureEvidenceLoadResult> {
  try {
    const response = await backendFetch("/official-disclosures/evidence-status?limit=50", {
      cache: "no-store",
    });
    if (!response.ok) return { status: "failed", payload: null };
    return {
      status: "loaded",
      payload: (await response.json()) as OfficialDisclosureEvidencePayload,
    };
  } catch {
    return { status: "failed", payload: null };
  }
}

function getSafeLocale(locale: string | undefined): string {
  if (!locale) {
    return FALLBACK_LOCALE;
  }

  try {
    const [supportedLocale] = Intl.DateTimeFormat.supportedLocalesOf([locale]);
    return supportedLocale ?? FALLBACK_LOCALE;
  } catch {
    return FALLBACK_LOCALE;
  }
}

function formatDate(
  value: string | null | undefined,
  locale: string,
  unavailableLabel: string,
): string {
  if (!value) {
    return unavailableLabel;
  }

  const parsedDate = new Date(value);
  return Number.isNaN(parsedDate.getTime())
    ? unavailableLabel
    : parsedDate.toLocaleDateString(getSafeLocale(locale));
}

function formatIndicatorValue(
  item: MarketOverviewIndicatorItem,
  locale: string,
  unavailableLabel: string,
): string {
  if (typeof item.value !== "number") {
    return unavailableLabel;
  }

  const formattedValue = new Intl.NumberFormat(locale, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(item.value);
  return item.unit === "percent" ? `${formattedValue}%` : formattedValue;
}

function hasNonEmptyComponent(
  components: Record<string, unknown> | undefined,
  keys: string[],
): boolean {
  if (!components) {
    return false;
  }

  return keys.some((key) => {
    const value = components[key];
    return (
      value !== undefined && value !== null && String(value).trim().length > 0
    );
  });
}

function hasAuditMetadata(item: MarketOverviewIndicatorItem): boolean {
  return (
    hasNonEmptyComponent(item.components, AUDIT_SOURCE_COMPONENT_KEYS) &&
    hasNonEmptyComponent(item.components, AUDIT_METHOD_COMPONENT_KEYS)
  );
}

function isIndicatorCitable(item: MarketOverviewIndicatorItem): boolean {
  return (
    item.status === "ok" &&
    typeof item.value === "number" &&
    Boolean(item.as_of) &&
    Boolean(item.source)
  );
}

function sourceMentionsIndicator(
  source: InformationSourceItem,
  code: string,
): boolean {
  if ((source.coverage ?? []).includes(code)) {
    return true;
  }

  return source.seed_template?.target_indicator_codes?.includes(code) ?? false;
}

function getIndicatorSourceStatuses(
  item: MarketOverviewIndicatorItem,
  informationSources: InformationSourcesPayload | null,
): string[] {
  return (informationSources?.items ?? [])
    .filter((source) => sourceMentionsIndicator(source, item.code))
    .map((source) => source.status);
}

function getIndicatorEvidenceState(
  item: MarketOverviewIndicatorItem,
  informationSources: InformationSourcesPayload | null,
): IndicatorEvidenceState {
  if (isIndicatorCitable(item)) {
    return "ai_citable";
  }
  if (item.status === "ok") {
    return "needs_review";
  }

  const sourceStatuses = getIndicatorSourceStatuses(item, informationSources);
  if (sourceStatuses.includes("needs_adapter")) {
    return "needs_adapter";
  }
  if (sourceStatuses.includes("needs_manual_seed")) {
    return "needs_manual_seed";
  }
  if (sourceStatuses.includes("future")) {
    return "future";
  }

  return "no_local_evidence";
}

function getIndicatorItems(
  payload: MarketOverviewPayload,
): MarketOverviewIndicatorItem[] {
  return (
    payload.macro_indicators?.items ?? payload.valuation_indicators?.items ?? []
  );
}

function getSourceGroups(informationSources: InformationSourcesPayload | null) {
  const groupsWithItems = (informationSources?.groups ?? []).filter(
    (group) => group.items.length > 0,
  );
  if (groupsWithItems.length > 0) {
    return groupsWithItems;
  }

  const items = informationSources?.items ?? [];
  if (items.length === 0) {
    return [];
  }

  const groups = new Map<string, InformationSourceItem[]>();
  for (const item of items) {
    groups.set(item.category, [...(groups.get(item.category) ?? []), item]);
  }

  return Array.from(groups.entries()).map(([category, groupItems]) => ({
    category,
    label: category.replaceAll("_", " "),
    items: groupItems,
  }));
}

function buildNotebookSourceTargets(
  informationSources: InformationSourcesPayload | null,
): ResearchSourceTargetOption[] {
  const seen = new Set<string>();
  return (informationSources?.items ?? []).flatMap((item) => {
    if (seen.has(item.id)) {
      return [];
    }
    seen.add(item.id);
    return [
      {
        id: item.id,
        label: item.label,
        category: item.category,
        status: item.status,
        targetIndicatorCodes:
          item.seed_template?.target_indicator_codes &&
          item.seed_template.target_indicator_codes.length > 0
            ? item.seed_template.target_indicator_codes
            : (item.coverage ?? []),
      },
    ];
  });
}

function getNoteMetadata(note: ResearchSourceNote): Record<string, unknown> {
  return note.metadata && typeof note.metadata === "object"
    ? note.metadata
    : {};
}

function getLinkedNotesForSource(
  sourceId: string,
  notes: ResearchSourceNote[],
): ResearchSourceNote[] {
  return notes.filter((note) => getNoteMetadata(note).source_id === sourceId);
}

function getNoteCompletenessStatus(note: ResearchSourceNote): string {
  const completeness = getNoteMetadata(note).completeness;
  if (
    !completeness ||
    typeof completeness !== "object" ||
    !("status" in completeness)
  ) {
    return "missing";
  }
  const status = completeness.status;
  return typeof status === "string" ? status : "missing";
}

function getRefreshCoverage(
  items: MarketOverviewIndicatorItem[],
  codes: string[],
) {
  const itemsByCode = new Map(items.map((item) => [item.code, item]));
  const matchedItems = codes
    .map((code) => itemsByCode.get(code))
    .filter(Boolean) as MarketOverviewIndicatorItem[];
  const citableCount = matchedItems.filter(isIndicatorCitable).length;
  const latestAsOf = matchedItems
    .map((item) => item.as_of)
    .filter((value): value is string => Boolean(value))
    .sort()
    .at(-1);

  return {
    citableCount,
    total: codes.length,
    missingCount: codes.length - citableCount,
    latestAsOf,
  };
}

function getSourcesByIds(
  informationSources: InformationSourcesPayload | null,
  sourceIds: Set<string>,
) {
  return (informationSources?.items ?? []).filter((item) =>
    sourceIds.has(item.id),
  );
}

function badgeVariantForStatus(
  status: string,
): "secondary" | "outline" | "destructive" {
  if (status === "ok" || status === "configured" || status === "ai_citable") {
    return "secondary";
  }
  if (
    status === "needs_configuration" ||
    status === "no_local_evidence" ||
    status === "no_data"
  ) {
    return "destructive";
  }
  return "outline";
}

function getOfficialMacroProviderStatus(
  payload: OfficialMacroSourceStatusPayload | null,
  provider: "fred" | "world_bank",
): OfficialMacroSourceStatusProvider | null {
  return payload?.providers.find((item) => item.provider === provider) ?? null;
}

function officialSourceStatusLabel(
  status: string,
  t: Awaited<ReturnType<typeof getTranslations>>,
): string {
  const labels: Record<string, string> = {
    ok: t("officialSourceStatusOk"),
    degraded: t("officialSourceStatusDegraded"),
    needs_configuration: t("officialSourceStatusNeedsConfiguration"),
    manual_or_future: t("officialSourceStatusManualOrFuture"),
  };
  return labels[status] ?? status;
}

function officialSourceRefreshLabel(
  sourceStatus: OfficialMacroSourceStatusProvider,
  t: Awaited<ReturnType<typeof getTranslations>>,
): string {
  return sourceStatus.can_refresh_from_browser
    ? t("officialSourceBrowserReady")
    : t("officialSourceBrowserBlocked");
}

function officialSourceCredentialLabel(
  sourceStatus: OfficialMacroSourceStatusProvider,
  t: Awaited<ReturnType<typeof getTranslations>>,
): string {
  if (!sourceStatus.credential_required) {
    return t("officialSourceCredentialNotRequired");
  }

  const credential = sourceStatus.credential_label ?? t("unavailableShort");
  return sourceStatus.credential_configured
    ? t("officialSourceCredentialConfigured", { credential })
    : t("officialSourceCredentialMissing", { credential });
}

function officialSourceFreshnessPolicy(
  sourceStatus: OfficialMacroSourceStatusProvider,
  t: Awaited<ReturnType<typeof getTranslations>>,
): string {
  return sourceStatus.provider === "world_bank"
    ? t("officialSourceWorldBankFreshnessPolicy")
    : t("officialSourceFredFreshnessPolicy");
}

function officialSourceNextAction(
  sourceStatus: OfficialMacroSourceStatusProvider,
  t: Awaited<ReturnType<typeof getTranslations>>,
): string {
  const missingCount = sourceStatus.missing_indicator_codes?.length ?? 0;
  if (sourceStatus.provider === "fred") {
    return sourceStatus.configured
      ? missingCount > 0
        ? t("officialSourceFredRunRefresh")
        : t("officialSourceFredUpToDate")
      : t("officialSourceFredConfigure");
  }

  return missingCount > 0
    ? t("officialSourceWorldBankRunRefresh")
    : t("officialSourceWorldBankUpToDate");
}

function renderOfficialSourceStatusPanel(
  sourceStatus: OfficialMacroSourceStatusProvider | null,
  t: Awaited<ReturnType<typeof getTranslations>>,
  locale: string,
) {
  if (sourceStatus === null) {
    return (
      <FinancialTerminalSurface className="mt-4 border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-200">
        {t("officialSourceStatusUnavailable")}
      </FinancialTerminalSurface>
    );
  }

  const missingCodes = sourceStatus.missing_indicator_codes ?? [];
  return (
    <div className="mt-4 space-y-3">
      <div className="grid gap-2 text-xs md:grid-cols-2">
        <FinancialTerminalSurface className="p-2">
          <div className="font-semibold uppercase text-muted-foreground">
            {t("officialSourceReadiness")}
          </div>
          <div className="mt-1 flex flex-wrap gap-2">
            <Badge variant={badgeVariantForStatus(sourceStatus.status)}>
              {officialSourceStatusLabel(sourceStatus.status, t)}
            </Badge>
            <Badge
              variant={
                sourceStatus.can_refresh_from_browser ? "secondary" : "outline"
              }
            >
              {officialSourceRefreshLabel(sourceStatus, t)}
            </Badge>
          </div>
        </FinancialTerminalSurface>
        <FinancialTerminalSurface className="p-2">
          <div className="font-semibold uppercase text-muted-foreground">
            {t("officialSourceCredential")}
          </div>
          <p className="mt-1">
            {officialSourceCredentialLabel(sourceStatus, t)}
          </p>
          {sourceStatus.base_url ? (
            <p className="mt-1 break-all text-muted-foreground">
              {t("officialSourceBaseUrl", { url: sourceStatus.base_url })}
            </p>
          ) : null}
        </FinancialTerminalSurface>
        <FinancialTerminalSurface className="p-2">
          <div className="font-semibold uppercase text-muted-foreground">
            {t("officialSourceEvidence")}
          </div>
          <p className="mt-1">
            {t("officialSourceEvidenceCount", {
              count: sourceStatus.evidence_count,
            })}
          </p>
          <p className="mt-1 text-muted-foreground">
            {t("officialSourceLatest", {
              date: formatDate(
                sourceStatus.latest_as_of,
                locale,
                t("unavailableShort"),
              ),
            })}
          </p>
        </FinancialTerminalSurface>
        <FinancialTerminalSurface className="p-2">
          <div className="font-semibold uppercase text-muted-foreground">
            {t("officialSourceCoverage")}
          </div>
          <p className="mt-1 break-words font-mono">
            {sourceStatus.indicator_codes.join(", ")}
          </p>
          {missingCodes.length > 0 ? (
            <p className="mt-1 break-words text-muted-foreground">
              {t("officialSourceMissingCodes", {
                codes: missingCodes.join(", "),
              })}
            </p>
          ) : null}
        </FinancialTerminalSurface>
      </div>
      <FinancialTerminalSurface className="p-3 text-xs text-muted-foreground">
        <p>
          <span className="font-semibold text-foreground">
            {t("officialSourceNextAction")}
          </span>{" "}
          {officialSourceNextAction(sourceStatus, t)}
        </p>
        <p className="mt-1">
          <span className="font-semibold text-foreground">
            {t("officialSourceFreshness")}
          </span>{" "}
          {officialSourceFreshnessPolicy(sourceStatus, t)}
        </p>
        <p className="mt-1">
          <span className="font-semibold text-foreground">
            {t("officialSourceCitationBoundary")}
          </span>{" "}
          {t("officialSourceCitationPolicy")}
        </p>
      </FinancialTerminalSurface>
    </div>
  );
}

function renderMetric(
  label: string,
  value: string | number,
  description: string,
) {
  return (
    <FinancialTerminalSurface className="p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 font-mono text-2xl font-semibold">{value}</div>
      <div className="mt-1 text-xs text-muted-foreground">{description}</div>
    </FinancialTerminalSurface>
  );
}

function renderBriefSectionList(brief: DashboardBriefPayload) {
  return brief.sections.map((section) => (
    <FinancialTerminalSurface key={section.id} className="p-3">
      <div className="text-sm font-semibold">{section.title}</div>
      <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-muted-foreground">
        {section.items.map((item, index) => (
          <li key={`${section.id}-${index}`}>{item}</li>
        ))}
      </ul>
    </FinancialTerminalSurface>
  ));
}

function renderOfficialRefreshPanel({
  title,
  description,
  commandLabel,
  command,
  dryRunLabel,
  dryRunCommand,
  coverage,
  coverageLabel,
  latestLabel,
  missingLabel,
  sourceItems,
  sourceStatusLabels,
  unavailableLabel,
  statusPanel,
  actions,
}: {
  title: string;
  description: string;
  commandLabel: string;
  command: string;
  dryRunLabel: string;
  dryRunCommand: string;
  coverage: ReturnType<typeof getRefreshCoverage>;
  coverageLabel: string;
  latestLabel: string;
  missingLabel: string;
  sourceItems: InformationSourceItem[];
  sourceStatusLabels: Record<string, string>;
  unavailableLabel: string;
  statusPanel?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <FinancialTerminalSurface className="p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-base font-semibold">{title}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        </div>
        <Badge variant={coverage.missingCount === 0 ? "secondary" : "outline"}>
          {coverageLabel}
        </Badge>
      </div>
      {statusPanel}
      <div className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
        <FinancialTerminalSurface className="p-2">
          <div className="text-xs font-semibold uppercase text-muted-foreground">
            {commandLabel}
          </div>
          <code className="mt-1 block break-all font-mono text-xs">
            {command}
          </code>
        </FinancialTerminalSurface>
        <FinancialTerminalSurface className="p-2">
          <div className="text-xs font-semibold uppercase text-muted-foreground">
            {dryRunLabel}
          </div>
          <code className="mt-1 block break-all font-mono text-xs">
            {dryRunCommand}
          </code>
        </FinancialTerminalSurface>
      </div>
      {actions}
      <div className="mt-4 flex flex-wrap gap-2 text-xs">
        <Badge variant="outline">{latestLabel}</Badge>
        <Badge
          variant={coverage.missingCount > 0 ? "destructive" : "secondary"}
        >
          {missingLabel}
        </Badge>
        {sourceItems.map((item) => (
          <Badge key={item.id} variant={badgeVariantForStatus(item.status)}>
            {item.label}: {sourceStatusLabels[item.status] ?? item.status}
          </Badge>
        ))}
        {sourceItems.length === 0 ? (
          <Badge variant="outline">{unavailableLabel}</Badge>
        ) : null}
      </div>
    </FinancialTerminalSurface>
  );
}

function renderOfficialRefreshGuidance(
  indicators: MarketOverviewIndicatorItem[],
  informationSources: InformationSourcesPayload | null,
  officialSourceStatus: OfficialMacroSourceStatusPayload | null,
  t: Awaited<ReturnType<typeof getTranslations>>,
  locale: string,
  sourceStatusLabels: Record<string, string>,
) {
  const unavailableLabel = t("unavailableShort");
  const fredCoverage = getRefreshCoverage(
    indicators,
    FRED_OFFICIAL_REFRESH_CODES,
  );
  const worldBankCoverage = getRefreshCoverage(
    indicators,
    WORLD_BANK_BUFFETT_REFRESH_CODES,
  );
  const fredSources = getSourcesByIds(
    informationSources,
    FRED_OFFICIAL_SOURCE_IDS,
  );
  const worldBankSources = getSourcesByIds(
    informationSources,
    WORLD_BANK_OFFICIAL_SOURCE_IDS,
  );
  const fredSourceStatus = getOfficialMacroProviderStatus(
    officialSourceStatus,
    "fred",
  );
  const worldBankSourceStatus = getOfficialMacroProviderStatus(
    officialSourceStatus,
    "world_bank",
  );
  const actionLabels = buildOfficialMacroRefreshLabels(t);

  return (
    <FinancialTerminalCard className="border-emerald-500/30">
      <FinancialTerminalCardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">{t("officialRefreshManualBadge")}</Badge>
          <Badge variant="outline">{t("officialRefreshWebActionBadge")}</Badge>
        </div>
        <CardTitle className="flex items-center gap-2 text-xl">
          <RefreshCw className="h-5 w-5" />
          {t("officialRefreshTitle")}
        </CardTitle>
        <CardDescription>{t("officialRefreshDescription")}</CardDescription>
      </FinancialTerminalCardHeader>
      <FinancialTerminalCardContent className="space-y-4">
        <div className="grid gap-3 xl:grid-cols-2">
          {renderOfficialRefreshPanel({
            title: t("officialRefreshFredTitle"),
            description: t("officialRefreshFredDescription"),
            commandLabel: t("officialRefreshWriteCommand"),
            command: t("officialRefreshFredCommand"),
            dryRunLabel: t("officialRefreshDryRunCommand"),
            dryRunCommand: t("officialRefreshFredDryRunCommand"),
            coverage: fredCoverage,
            coverageLabel: t("officialRefreshCoverage", {
              configured: fredCoverage.citableCount,
              total: fredCoverage.total,
            }),
            latestLabel: t("officialRefreshLatest", {
              date: formatDate(
                fredCoverage.latestAsOf,
                locale,
                unavailableLabel,
              ),
            }),
            missingLabel: t("officialRefreshMissing", {
              count: fredCoverage.missingCount,
            }),
            sourceItems: fredSources,
            sourceStatusLabels,
            unavailableLabel,
            statusPanel: renderOfficialSourceStatusPanel(
              fredSourceStatus,
              t,
              locale,
            ),
            actions: (
              <OfficialMacroRefreshActions
                endpoint="/api/market-indicators/official-refresh/fred"
                defaultPayload={{ series: "all", latest_only: true }}
                labels={actionLabels}
              />
            ),
          })}
          {renderOfficialRefreshPanel({
            title: t("officialRefreshWorldBankTitle"),
            description: t("officialRefreshWorldBankDescription"),
            commandLabel: t("officialRefreshWriteCommand"),
            command: t("officialRefreshWorldBankCommand"),
            dryRunLabel: t("officialRefreshDryRunCommand"),
            dryRunCommand: t("officialRefreshWorldBankDryRunCommand"),
            coverage: worldBankCoverage,
            coverageLabel: t("officialRefreshCoverage", {
              configured: worldBankCoverage.citableCount,
              total: worldBankCoverage.total,
            }),
            latestLabel: t("officialRefreshLatest", {
              date: formatDate(
                worldBankCoverage.latestAsOf,
                locale,
                unavailableLabel,
              ),
            }),
            missingLabel: t("officialRefreshMissing", {
              count: worldBankCoverage.missingCount,
            }),
            sourceItems: worldBankSources,
            sourceStatusLabels,
            unavailableLabel,
            statusPanel: renderOfficialSourceStatusPanel(
              worldBankSourceStatus,
              t,
              locale,
            ),
            actions: (
              <OfficialMacroRefreshActions
                endpoint="/api/market-indicators/official-refresh/world-bank"
                defaultPayload={{ target: "all", latest_only: true }}
                labels={actionLabels}
              />
            ),
          })}
        </div>
        <FinancialTerminalSurface className="p-3 text-sm text-muted-foreground">
          <div className="flex items-center gap-2 font-semibold text-foreground">
            <TerminalSquare className="h-4 w-4" />
            {t("officialRefreshRunbookTitle")}
          </div>
          <p className="mt-1">{t("officialRefreshRunbookPath")}</p>
          <p className="mt-2">{t("officialRefreshCitationBoundary")}</p>
          <p className="mt-2">{t("officialRefreshUnsupportedGap")}</p>
        </FinancialTerminalSurface>
      </FinancialTerminalCardContent>
    </FinancialTerminalCard>
  );
}

function buildOfficialMacroRefreshLabels(
  t: Awaited<ReturnType<typeof getTranslations>>,
): OfficialMacroRefreshActionsLabels {
  return {
    dryRunAction: t("officialRefreshDryRunAction"),
    dryRunRunning: t("officialRefreshDryRunRunning"),
    writeAction: t("officialRefreshWriteAction"),
    writeRunning: t("officialRefreshWriteRunning"),
    writeStoresObservation: t("officialRefreshWriteStoresObservation"),
    resultDryRun: t("officialRefreshResultDryRun"),
    resultWrite: t("officialRefreshResultWrite"),
    resultObservations: t("officialRefreshResultObservations", {
      count: "{count}",
    }),
    resultFetched: t("officialRefreshResultFetched", { count: "{count}" }),
    resultSkipped: t("officialRefreshResultSkipped", { count: "{count}" }),
    resultCodes: t("officialRefreshResultCodes", { codes: "{codes}" }),
    resultLatestAsOf: t("officialRefreshResultLatestAsOf", { date: "{date}" }),
    resultCacheCleared: t("officialRefreshResultCacheCleared", {
      count: "{count}",
    }),
    diagnosticsTitle: t("officialRefreshDiagnosticsTitle"),
    diagnosticsEmpty: t("officialRefreshDiagnosticsEmpty"),
    failed: t("officialRefreshFailed"),
    unavailableShort: t("unavailableShort"),
  };
}

function followUpKindLabel(
  kind: string | undefined,
  t: Awaited<ReturnType<typeof getTranslations>>,
): string {
  switch (kind) {
    case "source_review":
      return t("followUpKindSourceReview");
    case "seed_prep":
      return t("followUpKindSeedPrep");
    case "ai_summary_question":
      return t("followUpKindAiSummaryQuestion");
    case "source_gap":
      return t("followUpKindSourceGap");
    case "research_note":
      return t("followUpKindResearchNote");
    default:
      return kind ?? t("unavailableShort");
  }
}

function followUpPolicyLabel(
  policy: string | undefined,
  t: Awaited<ReturnType<typeof getTranslations>>,
): string {
  switch (policy) {
    case "citable":
      return t("followUpPolicyCitable");
    case "collection_only":
      return t("followUpPolicyCollectionOnly");
    case "guidance_only":
      return t("followUpPolicyGuidanceOnly");
    default:
      return policy ?? t("unavailableShort");
  }
}

function followUpPriorityLabel(
  priority: string | undefined,
  t: Awaited<ReturnType<typeof getTranslations>>,
): string {
  switch (priority) {
    case "high":
      return t("followUpPriorityHigh");
    case "medium":
      return t("followUpPriorityMedium");
    case "low":
      return t("followUpPriorityLow");
    default:
      return priority ?? t("unavailableShort");
  }
}

function followUpPolicyBadgeVariant(
  policy: string | undefined,
): "secondary" | "outline" | "destructive" {
  if (policy === "citable") {
    return "secondary";
  }
  if (policy === "collection_only" || policy === "guidance_only") {
    return "outline";
  }
  return "destructive";
}

function renderFollowUpMetadata(
  item: ResearchFollowUpQueueItem,
  t: Awaited<ReturnType<typeof getTranslations>>,
  locale: string,
) {
  const sourceLabel = item.source_label ?? item.source_name;
  const dateLabel = item.as_of ?? item.retrieved_at;
  return (
    <div className="mt-3 grid gap-2 text-xs text-muted-foreground md:grid-cols-2">
      {sourceLabel ? (
        <div>
          <span className="font-medium text-foreground">
            {t("followUpSource")}
          </span>{" "}
          {sourceLabel}
        </div>
      ) : null}
      {item.source_status ? (
        <div>
          <span className="font-medium text-foreground">
            {t("followUpSourceStatus")}
          </span>{" "}
          {item.source_status}
        </div>
      ) : null}
      {item.component_role ? (
        <div>
          <span className="font-medium text-foreground">
            {t("followUpComponentRole")}
          </span>{" "}
          {item.component_role}
        </div>
      ) : null}
      {item.completeness_status ? (
        <div>
          <span className="font-medium text-foreground">
            {t("followUpCompleteness")}
          </span>{" "}
          {item.completeness_status}
        </div>
      ) : null}
      {dateLabel ? (
        <div>
          <span className="font-medium text-foreground">
            {t("followUpDate")}
          </span>{" "}
          {formatDate(dateLabel, locale, t("unavailableShort"))}
        </div>
      ) : null}
      {typeof item.linked_note_count === "number" ? (
        <div>
          <span className="font-medium text-foreground">
            {t("followUpLinkedNotes")}
          </span>{" "}
          {item.linked_note_count}
        </div>
      ) : null}
      {typeof item.seed_ready_note_count === "number" ? (
        <div>
          <span className="font-medium text-foreground">
            {t("followUpSeedReadyNotes")}
          </span>{" "}
          {item.seed_ready_note_count}
        </div>
      ) : null}
      {item.citation_id ? (
        <div className="font-mono">
          <span className="font-sans font-medium text-foreground">
            {t("followUpCitation")}
          </span>{" "}
          {item.citation_id}
        </div>
      ) : null}
    </div>
  );
}

function renderResearchFollowUpQueue(
  queue: ResearchFollowUpQueuePayload | undefined,
  t: Awaited<ReturnType<typeof getTranslations>>,
  locale: string,
) {
  const summary = queue?.summary ?? {};
  const items = queue?.items ?? [];
  return (
    <FinancialTerminalCard>
      <FinancialTerminalCardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={queue?.status === "ok" ? "secondary" : "outline"}>
            {queue?.status ?? t("unavailableShort")}
          </Badge>
          {queue?.generated_at ? (
            <Badge variant="outline">
              {t("followUpGenerated", {
                date: formatDate(
                  queue.generated_at,
                  locale,
                  t("unavailableShort"),
                ),
              })}
            </Badge>
          ) : null}
        </div>
        <CardTitle className="flex items-center gap-2 text-xl">
          <ListChecks className="h-5 w-5" />
          {t("followUpTitle")}
        </CardTitle>
        <CardDescription>{t("followUpDescription")}</CardDescription>
      </FinancialTerminalCardHeader>
      <FinancialTerminalCardContent className="space-y-4">
        <div className="grid gap-3 md:grid-cols-4">
          {renderMetric(
            t("followUpTotal"),
            summary.total ?? 0,
            t("followUpTotalDesc"),
          )}
          {renderMetric(
            t("followUpAiQuestions"),
            summary.ai_summary_question ?? 0,
            t("followUpAiQuestionsDesc"),
          )}
          {renderMetric(
            t("followUpSeedPrep"),
            summary.seed_prep ?? 0,
            t("followUpSeedPrepDesc"),
          )}
          {renderMetric(
            t("followUpSourceGaps"),
            summary.source_gap ?? 0,
            t("followUpSourceGapsDesc"),
          )}
        </div>

        {items.length === 0 ? (
          <EmptyState
            title={t("followUpNoItems")}
            description={t("followUpNoItemsDesc")}
          />
        ) : (
          <div className="grid gap-3 xl:grid-cols-2">
            {items.map((item) => (
              <FinancialTerminalSurface key={item.id} className="p-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline">
                        {followUpKindLabel(item.kind, t)}
                      </Badge>
                      <Badge variant="outline">
                        {followUpPriorityLabel(item.priority, t)}
                      </Badge>
                      <Badge
                        variant={followUpPolicyBadgeVariant(
                          item.citation_policy,
                        )}
                      >
                        {followUpPolicyLabel(item.citation_policy, t)}
                      </Badge>
                    </div>
                    <h3 className="mt-2 font-semibold">
                      {item.title ?? item.note_title ?? item.source_label}
                    </h3>
                  </div>
                  <div className="font-mono text-xs text-muted-foreground">
                    {item.id}
                  </div>
                </div>
                {item.prompt ? (
                  <p className="mt-3 text-sm text-muted-foreground">
                    <span className="font-medium text-foreground">
                      {t("followUpPrompt")}
                    </span>{" "}
                    {item.prompt}
                  </p>
                ) : null}
                {item.next_action ? (
                  <p className="mt-2 text-sm">
                    <span className="font-medium">
                      {t("followUpNextAction")}
                    </span>{" "}
                    {item.next_action}
                  </p>
                ) : null}
                {(item.target_indicator_codes ?? []).length > 0 ? (
                  <div className="mt-3 flex flex-wrap gap-1">
                    {item.target_indicator_codes?.map((code) => (
                      <Badge
                        key={`${item.id}-${code}`}
                        variant="outline"
                        className="text-[10px]"
                      >
                        {code}
                      </Badge>
                    ))}
                  </div>
                ) : null}
                {renderFollowUpMetadata(item, t, locale)}
              </FinancialTerminalSurface>
            ))}
          </div>
        )}

        <FinancialTerminalSurface className="p-3 text-sm text-muted-foreground">
          <div className="font-semibold text-foreground">
            {t("followUpSafetyTitle")}
          </div>
          <p className="mt-1">{t("followUpSafetyDescription")}</p>
        </FinancialTerminalSurface>
      </FinancialTerminalCardContent>
    </FinancialTerminalCard>
  );
}

function buildSeedImportLabels(
  t: Awaited<ReturnType<typeof getTranslations>>,
): EvidenceSeedImportReviewLabels {
  return {
    title: t("title"),
    description: t("description"),
    fileLabel: t("fileLabel"),
    fileButton: t("fileButton"),
    selectedFile: t("selectedFile", { name: "{name}" }),
    pasteLabel: t("pasteLabel"),
    pastePlaceholder: t("pastePlaceholder"),
    formatLabel: t("formatLabel"),
    formatAuto: t("formatAuto"),
    formatJson: t("formatJson"),
    formatCsv: t("formatCsv"),
    previewAction: t("previewAction"),
    previewing: t("previewing"),
    importAction: t("importAction"),
    importing: t("importing"),
    clearAction: t("clearAction"),
    contentRequired: t("contentRequired"),
    fileReadFailed: t("fileReadFailed"),
    previewFailed: t("previewFailed"),
    importFailed: t("importFailed"),
    importSuccess: t("importSuccess"),
    invalidNoImport: t("invalidNoImport"),
    overwriteWarning: t("overwriteWarning"),
    overwriteCheckbox: t("overwriteCheckbox"),
    citationBoundary: t("citationBoundary"),
    summaryRows: t("summaryRows"),
    summaryValid: t("summaryValid"),
    summaryInvalid: t("summaryInvalid"),
    summaryInserts: t("summaryInserts"),
    summaryUpdates: t("summaryUpdates"),
    rowColumn: t("rowColumn"),
    stateColumn: t("stateColumn"),
    intentColumn: t("intentColumn"),
    indicatorColumn: t("indicatorColumn"),
    asOfColumn: t("asOfColumn"),
    valueColumn: t("valueColumn"),
    sourceColumn: t("sourceColumn"),
    metadataColumn: t("metadataColumn"),
    errorsColumn: t("errorsColumn"),
    stateValid: t("stateValid"),
    stateInvalid: t("stateInvalid"),
    intentInsert: t("intentInsert"),
    intentUpdate: t("intentUpdate"),
    intentInvalid: t("intentInvalid"),
    metadataComplete: t("metadataComplete"),
    metadataMissing: t("metadataMissing"),
    noRows: t("noRows"),
    returnToEvidence: t("returnToEvidence"),
    unavailableShort: t("unavailableShort"),
  };
}

function buildNotebookLabels(
  t: Awaited<ReturnType<typeof getTranslations>>,
): ResearchSourceNotebookLabels {
  return {
    title: t("title"),
    description: t("description"),
    ingestionTitle: t("ingestionTitle"),
    ingestionDescription: t("ingestionDescription"),
    acceptedFormats: t("acceptedFormats"),
    extractAction: t("extractAction"),
    extracting: t("extracting"),
    extractFailed: t("extractFailed"),
    extractionContentRequired: t("extractionContentRequired"),
    applyExtraction: t("applyExtraction"),
    extractionBoundary: t("extractionBoundary"),
    extractionStatusOk: t("extractionStatusOk"),
    extractionStatusFallback: t("extractionStatusFallback"),
    extractionStatusInvalid: t("extractionStatusInvalid"),
    extractionModelLlm: t("extractionModelLlm"),
    extractionModelFallback: t("extractionModelFallback"),
    extractionFallbackReason: t("extractionFallbackReason", {
      reason: "{reason}",
    }),
    extractionSummaryTitle: t("extractionSummaryTitle"),
    extractionIndicatorsTitle: t("extractionIndicatorsTitle"),
    extractionCitationCluesTitle: t("extractionCitationCluesTitle"),
    extractionFollowUpsTitle: t("extractionFollowUpsTitle"),
    extractionSuggestedFieldsTitle: t("extractionSuggestedFieldsTitle"),
    extractionDiagnosticsTitle: t("extractionDiagnosticsTitle"),
    selectedFile: t("selectedFile", { name: "{name}" }),
    fileLabel: t("fileLabel"),
    fileReadFailed: t("fileReadFailed"),
    titleLabel: t("titleLabel"),
    titlePlaceholder: t("titlePlaceholder"),
    sourceNameLabel: t("sourceNameLabel"),
    sourceNamePlaceholder: t("sourceNamePlaceholder"),
    sourceTypeLabel: t("sourceTypeLabel"),
    sourceTypePlaceholder: t("sourceTypePlaceholder"),
    sourceUrlLabel: t("sourceUrlLabel"),
    sourceUrlPlaceholder: t("sourceUrlPlaceholder"),
    sourceTargetLabel: t("sourceTargetLabel"),
    sourceTargetPlaceholder: t("sourceTargetPlaceholder"),
    targetIndicatorsLabel: t("targetIndicatorsLabel"),
    targetIndicatorsPlaceholder: t("targetIndicatorsPlaceholder"),
    componentRoleLabel: t("componentRoleLabel"),
    componentRoleGeneral: t("componentRoleGeneral"),
    componentRoleMarketCap: t("componentRoleMarketCap"),
    componentRoleGdp: t("componentRoleGdp"),
    componentRoleCpi: t("componentRoleCpi"),
    componentRoleM2: t("componentRoleM2"),
    componentRoleRate: t("componentRoleRate"),
    componentRoleYieldSpread: t("componentRoleYieldSpread"),
    componentRoleFiling: t("componentRoleFiling"),
    componentRoleContext: t("componentRoleContext"),
    symbolsLabel: t("symbolsLabel"),
    symbolsPlaceholder: t("symbolsPlaceholder"),
    tagsLabel: t("tagsLabel"),
    tagsPlaceholder: t("tagsPlaceholder"),
    asOfLabel: t("asOfLabel"),
    publishedAtLabel: t("publishedAtLabel"),
    excerptLabel: t("excerptLabel"),
    excerptPlaceholder: t("excerptPlaceholder"),
    noteLabel: t("noteLabel"),
    notePlaceholder: t("notePlaceholder"),
    methodologyNoteLabel: t("methodologyNoteLabel"),
    methodologyNotePlaceholder: t("methodologyNotePlaceholder"),
    licenseNoteLabel: t("licenseNoteLabel"),
    licenseNotePlaceholder: t("licenseNotePlaceholder"),
    aiFollowUpLabel: t("aiFollowUpLabel"),
    aiFollowUpPlaceholder: t("aiFollowUpPlaceholder"),
    reviewStatusLabel: t("reviewStatusLabel"),
    statusDraft: t("statusDraft"),
    statusReviewed: t("statusReviewed"),
    statusArchived: t("statusArchived"),
    citableLabel: t("citableLabel"),
    saveAction: t("saveAction"),
    saving: t("saving"),
    clearAction: t("clearAction"),
    saveSuccess: t("saveSuccess"),
    saveFailed: t("saveFailed"),
    contentRequired: t("contentRequired"),
    citableBoundary: t("citableBoundary"),
    recentTitle: t("recentTitle"),
    loadFailed: t("loadFailed"),
    noNotes: t("noNotes"),
    filterLabel: t("filterLabel"),
    filterPlaceholder: t("filterPlaceholder"),
    statusFilterLabel: t("statusFilterLabel"),
    allStatuses: t("allStatuses"),
    citableOnlyLabel: t("citableOnlyLabel"),
    citableBadge: t("citableBadge"),
    collectionBadge: t("collectionBadge"),
    citationId: t("citationId", { id: "{id}" }),
    sourceLink: t("sourceLink"),
    linkedSourceBadge: t("linkedSourceBadge", { label: "{label}" }),
    targetIndicatorsBadge: t("targetIndicatorsBadge", { code: "{code}" }),
    componentRoleBadge: t("componentRoleBadge", { role: "{role}" }),
    reviewChecklistTitle: t("reviewChecklistTitle"),
    completenessSummary: t("completenessSummary", {
      score: "{score}",
      total: "{total}",
    }),
    completenessComplete: t("completenessComplete"),
    completenessPartial: t("completenessPartial"),
    completenessMissing: t("completenessMissing"),
    checklistSourceIdentity: t("checklistSourceIdentity"),
    checklistSourceUrlOrDocument: t("checklistSourceUrlOrDocument"),
    checklistDateMetadata: t("checklistDateMetadata"),
    checklistExcerpt: t("checklistExcerpt"),
    checklistMethodology: t("checklistMethodology"),
    checklistTargets: t("checklistTargets"),
    checklistLicenseNote: t("checklistLicenseNote"),
    unavailableShort: t("unavailableShort"),
  };
}

function buildResearchBriefInboxLabels(
  t: Awaited<ReturnType<typeof getTranslations>>,
): ResearchBriefInboxLabels {
  return {
    title: t("title"),
    description: t("description"),
    generateAction: t("generateAction"),
    generating: t("generating"),
    generateSuccess: t("generateSuccess"),
    generateFailed: t("generateFailed"),
    loadFailedTitle: t("loadFailedTitle"),
    loadFailedDescription: t("loadFailedDescription"),
    emptyTitle: t("emptyTitle"),
    emptyDescription: t("emptyDescription"),
    createdAt: t("createdAt", { date: "{date}" }),
    modelGenerated: t("modelGenerated"),
    modelFallback: t("modelFallback"),
    modelName: t("modelName", { name: "{name}" }),
    citationsCount: t("citationsCount"),
    sourceGapsCount: t("sourceGapsCount"),
    diagnosticsCount: t("diagnosticsCount"),
    contentTitle: t("contentTitle"),
    safetyTitle: t("safetyTitle"),
    safetyNotAdvice: t("safetyNotAdvice"),
    safetyNoTrading: t("safetyNoTrading"),
    safetyNoFabricatedData: t("safetyNoFabricatedData"),
    unavailableShort: t("unavailableShort"),
  };
}

function buildMarketDailyEvidenceLabels(
  t: Awaited<ReturnType<typeof getTranslations>>,
): MarketDailyEvidencePanelLabels {
  return {
    title: t("title"),
    description: t("description"),
    maintenanceSummary: t("maintenanceSummary"),
    refreshAction: t("refreshAction"),
    refreshing: t("refreshing"),
    totalRows: t("totalRows"),
    latestImport: t("latestImport"),
    latestTradeDate: t("latestTradeDate"),
    citationsTitle: t("citationsTitle"),
    emptyTitle: t("emptyTitle"),
    emptyDescription: t("emptyDescription"),
    loadFailedTitle: t("loadFailedTitle"),
    loadFailedDescription: t("loadFailedDescription"),
    persistedOnly: t("persistedOnly"),
    notAdvice: t("notAdvice"),
    refreshSuccess: t("refreshSuccess"),
    insertedCount: t("insertedCount", { count: "{count}" }),
    updatedCount: t("updatedCount", { count: "{count}" }),
    skippedCount: t("skippedCount", { count: "{count}" }),
    diagnosticsTitle: t("diagnosticsTitle"),
    diagnosticsEmpty: t("diagnosticsEmpty"),
    refreshFailed: t("refreshFailed"),
    unavailableShort: t("unavailableShort"),
    corporateReportPeriod: t("corporateReportPeriod"),
    refreshCorporateActions: t("refreshCorporateActions"),
    refreshingCorporateActions: t("refreshingCorporateActions"),
    corporateActionQueued: t("corporateActionQueued"),
    openTaskRun: t("openTaskRun"),
    eventTypeLabels: {
      stock_fund_flow: t("eventStockFundFlow"),
      limit_up_reason: t("eventLimitUpReason"),
      dragon_tiger_list: t("eventDragonTigerList"),
      block_trade: t("eventBlockTrade"),
      hot_sector: t("eventHotSector"),
      dividend_bonus: t("eventDividendBonus"),
      rights_allotment: t("eventRightsAllotment"),
    },
  };
}

function buildOfficialDisclosureEvidenceLabels(
  t: Awaited<ReturnType<typeof getTranslations>>,
): OfficialDisclosureEvidenceLabels {
  return {
    title: t("title"),
    description: t("description"),
    maintenanceSummary: t("maintenanceSummary"),
    batchAction: t("batchAction"),
    batchPending: t("batchPending"),
    batchQueued: t("batchQueued"),
    monitorAction: t("monitorAction"),
    monitorPending: t("monitorPending"),
    monitoringTitle: t("monitoringTitle"),
    monitoringDescription: t("monitoringDescription"),
    freshSymbols: t("freshSymbols"),
    staleSymbols: t("staleSymbols"),
    backoffSymbols: t("backoffSymbols"),
    newDisclosures: t("newDisclosures"),
    lastSuccess: t("lastSuccess"),
    openTaskRun: t("openTaskRun"),
    eligibleSymbols: t("eligibleSymbols"),
    metadataRows: t("metadataRows"),
    extractedDocuments: t("extractedDocuments"),
    citableSections: t("citableSections"),
    symbol: t("symbol"),
    disclosure: t("disclosure"),
    publishedAt: t("publishedAt"),
    status: t("status"),
    sections: t("sections"),
    action: t("action"),
    ingestAction: t("ingestAction"),
    ingestPending: t("ingestPending"),
    officialSource: t("officialSource"),
    emptyTitle: t("emptyTitle"),
    emptyDescription: t("emptyDescription"),
    loadFailedTitle: t("loadFailedTitle"),
    loadFailedDescription: t("loadFailedDescription"),
    operationFailed: t("operationFailed"),
    metadataBoundary: t("metadataBoundary"),
    contentBoundary: t("contentBoundary"),
    watchlistOnly: t("watchlistOnly"),
    statusLabels: {
      metadata_only: t("statusMetadataOnly"),
      extracted: t("statusExtracted"),
      no_text: t("statusNoText"),
      rejected: t("statusRejected"),
      failed: t("statusFailed"),
    },
    freshnessLabels: {
      fresh: t("freshnessFresh"),
      stale: t("freshnessStale"),
      backoff: t("freshnessBackoff"),
      never: t("freshnessNever"),
    },
  };
}

function buildMacroDashboardLabels(
  macroT: Awaited<ReturnType<typeof getTranslations>>,
  dashboardT: Awaited<ReturnType<typeof getTranslations>>,
  unavailable: string,
): MacroEconomicDashboardLabels {
  return {
    title: macroT("title"),
    description: macroT("description"),
    available: macroT("available"),
    missing: macroT("missing"),
    stale: macroT("stale"),
    latest: macroT("latest"),
    groupLabels: {
      rates: macroT("groupRates"),
      fundamentals: macroT("groupFundamentals"),
      valuation: macroT("groupValuation"),
      external: macroT("groupExternal"),
      money: macroT("groupMoney"),
      fiscal: macroT("groupFiscal"),
    },
    indicatorLabels: Object.fromEntries(
      Object.entries(BUILT_IN_MACRO_LABEL_KEYS).map(([code, key]) => [
        code,
        dashboardT(key),
      ]),
    ),
    fresh: macroT("fresh"),
    staleState: macroT("staleState"),
    noData: macroT("noData"),
    asOf: macroT("asOf", { date: "{date}" }),
    source: macroT("source", { source: "{source}" }),
    changeUp: macroT("changeUp", { value: "{value}" }),
    changeDown: macroT("changeDown", { value: "{value}" }),
    changeFlat: macroT("changeFlat"),
    trendSummary: macroT("trendSummary", {
      name: "{name}",
      count: "{count}",
    }),
    refresh: macroT("refresh"),
    refreshing: macroT("refreshing"),
    refreshSuccess: macroT("refreshSuccess", { count: "{count}" }),
    refreshDegraded: macroT("refreshDegraded", { count: "{count}" }),
    refreshFailed: macroT("refreshFailed"),
    unavailable,
  };
}

export default async function EvidenceCenterPage({
  params = Promise.resolve({ locale: "en" }),
  searchParams = Promise.resolve({}),
}: EvidenceCenterPageProps = {}) {
  const [
    { locale: requestedLocale },
    query,
    platformSettings,
    t,
    seedImportT,
    notebookT,
    researchBriefT,
    marketDailyEvidenceT,
    officialDisclosureEvidenceT,
    macroDashboardT,
    economicCalendarT,
    industryRankingT,
    dashboardT,
  ] = await Promise.all([
    params,
    searchParams,
    getPlatformSettings(),
    getTranslations("EvidenceCenter"),
    getTranslations("EvidenceSeedImport"),
    getTranslations("ResearchSourceNotebook"),
    getTranslations("ResearchBriefInbox"),
    getTranslations("MarketDailyEvidence"),
    getTranslations("OfficialDisclosureEvidence"),
    getTranslations("MacroDashboard"),
    getTranslations("EconomicCalendar"),
    getTranslations("IndustryRankingHistory"),
    getTranslations("Dashboard"),
  ]);
  const locale = getSafeLocale(requestedLocale);
  const provider =
    query.provider?.trim() || platformSettings.market_data_provider;
  const [
    marketOverviewResult,
    officialSourceStatusResult,
    researchSourceNotesResult,
    researchBriefsResult,
    marketDailyEvidenceResult,
    officialDisclosureEvidenceResult,
    macroDashboardResult,
    economicCalendarResult,
    industryRankingResult,
  ] = await Promise.all([
    fetchMarketOverview(provider),
    fetchOfficialMacroSourceStatus(),
    fetchResearchSourceNotes(),
    fetchResearchBriefs(),
    fetchMarketDailyEvidence(),
    fetchOfficialDisclosureEvidence(),
    fetchMacroDashboard(),
    fetchEconomicCalendar(),
    fetchIndustryRankings(),
  ]);

  const marketOverviewUnavailable = marketOverviewResult.status === "failed";
  const payload: MarketOverviewPayload =
    marketOverviewResult.status === "loaded"
      ? marketOverviewResult.payload
      : {
          generated_at: "",
          provider,
          macro_indicators: { items: [] },
          valuation_indicators: { items: [] },
        };
  const indicators = getIndicatorItems(payload);
  const dashboardBrief = payload.dashboard_brief ?? null;
  const informationSources = payload.information_sources ?? null;
  const officialSourceStatus =
    officialSourceStatusResult.status === "loaded"
      ? officialSourceStatusResult.payload
      : null;
  const sourceGroups = getSourceGroups(informationSources);
  const sourceTargetOptions = buildNotebookSourceTargets(informationSources);
  const macroDashboardSummary =
    macroDashboardResult.status === "loaded"
      ? macroDashboardResult.payload.summary
      : null;
  const sourceStatusLabels: Record<string, string> = {
    configured: t("sourceStatusConfigured"),
    needs_adapter: t("sourceStatusNeedsAdapter"),
    needs_manual_seed: t("sourceStatusNeedsManualSeed"),
    no_data: t("sourceStatusNoData"),
    future: t("sourceStatusFuture"),
  };
  const evidenceStateLabels: Record<IndicatorEvidenceState, string> = {
    ai_citable: t("stateAiCitable"),
    needs_adapter: t("stateNeedsAdapter"),
    needs_manual_seed: t("stateNeedsManualSeed"),
    no_local_evidence: t("stateNoLocalEvidence"),
    future: t("stateFuture"),
    needs_review: t("stateNeedsReview"),
  };

  return (
    <div className="space-y-6">
      <FinancialPageHeader
        title={t("title")}
        description={t("description")}
        badges={[
          { label: t("badge"), variant: "secondary" },
          { label: t("activeProvider", { provider }) },
          ...(!marketOverviewUnavailable
            ? [
                {
                  label: t("generatedAt", {
                    date: formatDate(
                      payload.generated_at,
                      locale,
                      t("unavailableShort"),
                    ),
                  }),
                },
              ]
            : []),
        ]}
        metrics={[
          {
            label: t("metricIndicators"),
            value: macroDashboardSummary?.total ?? t("unavailableShort"),
            description: t("metricIndicatorsDesc"),
          },
          {
            label: t("metricCitable"),
            value: macroDashboardSummary?.available ?? t("unavailableShort"),
            description: t("metricCitableDesc"),
          },
          {
            label: t("metricMissing"),
            value: macroDashboardSummary?.missing ?? t("unavailableShort"),
            description: t("metricMissingDesc"),
          },
          {
            label: t("metricSourcesNeedAction"),
            value: marketOverviewUnavailable
              ? t("unavailableShort")
              : (informationSources?.summary?.needs_action ?? 0),
            description: t("metricSourcesNeedActionDesc"),
          },
        ]}
        actions={
          <>
            {marketOverviewUnavailable ? (
              <Button size="sm" variant="outline" asChild>
                <Link href="/settings">{t("openSettings")}</Link>
              </Button>
            ) : null}
            <Button size="sm" variant="outline" asChild>
              <Link href="/reports">{t("openReports")}</Link>
            </Button>
            <Button size="sm" variant="outline" asChild>
              <Link href="/task-runs">{t("openTaskRuns")}</Link>
            </Button>
          </>
        }
      />

      {marketOverviewUnavailable ? (
        <ErrorState
          title={t("loadFailedTitle")}
          description={t("partialLoadDescription")}
        />
      ) : null}

      {macroDashboardResult.status === "loaded" ? (
        <MacroEconomicDashboard
          payload={macroDashboardResult.payload}
          locale={locale}
          labels={buildMacroDashboardLabels(
            macroDashboardT,
            dashboardT,
            t("unavailableShort"),
          )}
        />
      ) : (
        <ErrorState
          title={macroDashboardT("loadFailedTitle")}
          description={macroDashboardT("loadFailedDescription")}
        />
      )}

      {economicCalendarResult.status === "loaded" ? (
        <EconomicCalendarPanel
          payload={economicCalendarResult.payload}
          locale={locale}
          labels={{
            title: economicCalendarT("title"), description: economicCalendarT("description"), refresh: economicCalendarT("refresh"), refreshing: economicCalendarT("refreshing"),
            refreshSuccess: economicCalendarT("refreshSuccess", { count: "{count}" }), refreshFailed: economicCalendarT("refreshFailed"), allCountries: economicCalendarT("allCountries"),
            allImportance: economicCalendarT("allImportance"), importance: economicCalendarT("importance"), time: economicCalendarT("time"), country: economicCalendarT("country"), event: economicCalendarT("event"),
            previous: economicCalendarT("previous"), forecast: economicCalendarT("forecast"), actual: economicCalendarT("actual"), empty: economicCalendarT("empty"), unavailable: t("unavailableShort"),
          }}
        />
      ) : <ErrorState title={economicCalendarT("loadFailedTitle")} description={economicCalendarT("loadFailedDescription")} />}

      {industryRankingResult.status === "loaded" ? <IndustryRankingHistoryPanel payload={industryRankingResult.payload} labels={{ title: industryRankingT("title"), description: industryRankingT("description"), refresh: industryRankingT("refresh"), refreshing: industryRankingT("refreshing"), empty: industryRankingT("empty"), rank: industryRankingT("rank"), failed: industryRankingT("failed") }} /> : <ErrorState title={industryRankingT("loadFailedTitle")} description={industryRankingT("loadFailedDescription")} />}

      <details className="rounded-md border border-border/80 bg-card/70 p-4">
        <summary className="cursor-pointer text-sm font-semibold text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          {macroDashboardT("maintenanceSummary")}
        </summary>
        <div className="mt-4 space-y-6">

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(22rem,0.85fr)]">
        <FinancialTerminalCard>
          <FinancialTerminalCardHeader>
            <div className="flex flex-wrap items-center gap-2">
              <Badge
                variant={
                  dashboardBrief?.status === "ok" ? "secondary" : "outline"
                }
              >
                {dashboardBrief?.status ?? t("unavailableShort")}
              </Badge>
              {dashboardBrief ? (
                <Badge variant="outline">
                  {formatDate(
                    dashboardBrief.generated_at,
                    locale,
                    t("unavailableShort"),
                  )}
                </Badge>
              ) : null}
            </div>
            <CardTitle className="flex items-center gap-2 text-xl">
              <SearchCheck className="h-5 w-5" />
              {t("briefTitle")}
            </CardTitle>
            <CardDescription>{t("briefDescription")}</CardDescription>
          </FinancialTerminalCardHeader>
          <FinancialTerminalCardContent className="space-y-4">
            {dashboardBrief?.narrative?.answer_markdown ? (
              <FinancialTerminalSurface className="border-primary/30 bg-primary/5 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <div className="text-sm font-semibold">
                    {t("briefNarrative")}
                  </div>
                  <Badge
                    variant={
                      dashboardBrief.narrative.model.used_llm
                        ? "secondary"
                        : "outline"
                    }
                    className="text-[10px]"
                  >
                    {dashboardBrief.narrative.model.used_llm
                      ? t("modelGenerated")
                      : t("modelFallback")}
                  </Badge>
                  {dashboardBrief.narrative.model.name ? (
                    <Badge variant="outline" className="text-[10px]">
                      {t("modelName", {
                        name: dashboardBrief.narrative.model.name,
                      })}
                    </Badge>
                  ) : null}
                </div>
                <div className="mt-3 whitespace-pre-wrap text-sm leading-6">
                  {dashboardBrief.narrative.answer_markdown}
                </div>
                {dashboardBrief.narrative.model.fallback_reason ? (
                  <p className="mt-2 text-xs text-muted-foreground">
                    {dashboardBrief.narrative.model.fallback_reason}
                  </p>
                ) : null}
              </FinancialTerminalSurface>
            ) : (
              <EmptyState
                title={t("briefNarrativeUnavailable")}
                description={t("briefNarrativeUnavailableDesc")}
              />
            )}

            {dashboardBrief?.narrative?.context?.source_mix ? (
              <div className="grid gap-2 text-sm sm:grid-cols-4">
                <FinancialTerminalSurface className="p-2">
                  {t("macroEvidence", {
                    count:
                      dashboardBrief.narrative.context.source_mix
                        .macro_citations ?? 0,
                  })}
                </FinancialTerminalSurface>
                <FinancialTerminalSurface className="p-2">
                  {t("reportEvidence", {
                    count:
                      dashboardBrief.narrative.context.source_mix
                        .report_citations ?? 0,
                  })}
                </FinancialTerminalSurface>
                <FinancialTerminalSurface className="p-2">
                  {t("newsEvidence", {
                    count:
                      dashboardBrief.narrative.context.source_mix
                        .news_citations ?? 0,
                  })}
                </FinancialTerminalSurface>
                <FinancialTerminalSurface className="p-2">
                  {t("sourceGaps", {
                    count:
                      dashboardBrief.narrative.context.source_mix
                        .information_source_gaps ?? 0,
                  })}
                </FinancialTerminalSurface>
              </div>
            ) : null}

            {dashboardBrief ? (
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                {renderBriefSectionList(dashboardBrief)}
              </div>
            ) : null}
          </FinancialTerminalCardContent>
        </FinancialTerminalCard>

        <FinancialTerminalCard>
          <FinancialTerminalCardHeader>
            <CardTitle className="flex items-center gap-2 text-xl">
              <ShieldCheck className="h-5 w-5" />
              {t("briefEvidenceTitle")}
            </CardTitle>
            <CardDescription>{t("briefEvidenceDescription")}</CardDescription>
          </FinancialTerminalCardHeader>
          <FinancialTerminalCardContent className="space-y-4">
            {(dashboardBrief?.citations?.length ?? 0) > 0 ? (
              <div className="space-y-2">
                <div className="text-sm font-semibold">
                  {t("citationsTitle")}
                </div>
                <div className="flex flex-wrap gap-2">
                  {dashboardBrief?.citations?.map((citation) => (
                    <Badge key={citation.id} variant="outline">
                      {citation.label}
                    </Badge>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                {t("noCitations")}
              </p>
            )}

            {(dashboardBrief?.diagnostics?.length ?? 0) > 0 ? (
              <FinancialTerminalSurface className="border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-200">
                <div className="font-semibold">{t("diagnosticsTitle")}</div>
                <ul className="mt-2 list-disc space-y-1 pl-4">
                  {dashboardBrief?.diagnostics?.map((diagnostic, index) => (
                    <li
                      key={`${diagnostic.source ?? "diagnostic"}-${diagnostic.code ?? index}`}
                    >
                      {diagnostic.code ? `${diagnostic.code}: ` : null}
                      {diagnostic.message ??
                        diagnostic.status ??
                        t("unavailableShort")}
                    </li>
                  ))}
                </ul>
              </FinancialTerminalSurface>
            ) : null}

            {dashboardBrief?.safety ? (
              <div className="space-y-2 text-sm">
                <div className="font-semibold">{t("safetyTitle")}</div>
                <div className="flex flex-wrap gap-2">
                  {dashboardBrief.safety.not_investment_advice ? (
                    <Badge variant="secondary">{t("safetyNotAdvice")}</Badge>
                  ) : null}
                  {dashboardBrief.safety.no_buy_sell_hold ? (
                    <Badge variant="secondary">
                      {t("safetyNoTradingInstruction")}
                    </Badge>
                  ) : null}
                  {dashboardBrief.safety.no_fabricated_macro_data ? (
                    <Badge variant="secondary">
                      {t("safetyNoFabricatedData")}
                    </Badge>
                  ) : null}
                </div>
              </div>
            ) : null}
          </FinancialTerminalCardContent>
        </FinancialTerminalCard>
      </section>

      <ResearchBriefInbox
        labels={buildResearchBriefInboxLabels(researchBriefT)}
        initialBriefs={researchBriefsResult.items}
        loadFailed={researchBriefsResult.status === "failed"}
        provider={provider}
        locale={locale}
      />

      <ResearchSourceNotebook
        labels={buildNotebookLabels(notebookT)}
        initialNotes={researchSourceNotesResult.items}
        sourceTargets={sourceTargetOptions}
        loadFailed={researchSourceNotesResult.status === "failed"}
      />

      {renderResearchFollowUpQueue(
        payload.research_follow_up_queue,
        t,
        locale,
      )}

      <MarketDailyEvidencePanel
        labels={buildMarketDailyEvidenceLabels(marketDailyEvidenceT)}
        initialPayload={marketDailyEvidenceResult.payload}
        loadFailed={marketDailyEvidenceResult.status === "failed"}
      />

      <OfficialDisclosureEvidencePanel
        labels={buildOfficialDisclosureEvidenceLabels(officialDisclosureEvidenceT)}
        initialPayload={officialDisclosureEvidenceResult.payload}
        loadFailed={officialDisclosureEvidenceResult.status === "failed"}
      />

      <details className="rounded-md border border-dashed border-border/80 bg-card/95 p-4">
        <summary className="cursor-pointer text-sm font-semibold text-foreground">
          {t("advancedMaintenanceSummary")}
        </summary>
        <div className="mt-4 space-y-4">
          {renderOfficialRefreshGuidance(
            indicators,
            informationSources,
            officialSourceStatus,
            t,
            locale,
            sourceStatusLabels,
          )}

          <FinancialTerminalCard>
        <FinancialTerminalCardHeader>
          <CardTitle className="flex items-center gap-2 text-xl">
            <Database className="h-5 w-5" />
            {t("indicatorTableTitle")}
          </CardTitle>
          <CardDescription>{t("indicatorTableDescription")}</CardDescription>
        </FinancialTerminalCardHeader>
        <FinancialTerminalCardContent className="p-0">
          {indicators.length === 0 ? (
            <div className="p-4">
              <EmptyState
                title={t("noIndicators")}
                description={t("noIndicatorsDesc")}
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("columnIndicator")}</TableHead>
                    <TableHead>{t("columnState")}</TableHead>
                    <TableHead>{t("columnValue")}</TableHead>
                    <TableHead>{t("columnAsOf")}</TableHead>
                    <TableHead>{t("columnSource")}</TableHead>
                    <TableHead>{t("columnMetadata")}</TableHead>
                    <TableHead>{t("columnGap")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {indicators.map((item) => {
                    const evidenceState = getIndicatorEvidenceState(
                      item,
                      informationSources,
                    );
                    const metadataPresent = hasAuditMetadata(item);
                    return (
                      <TableRow key={item.code}>
                        <TableCell className="min-w-56">
                          <div className="font-medium">{item.name}</div>
                          <div className="font-mono text-xs text-muted-foreground">
                            {item.code}
                          </div>
                          <div className="mt-1 text-xs text-muted-foreground">
                            {[item.region, item.category]
                              .filter(Boolean)
                              .join(" / ") || t("unavailableShort")}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={badgeVariantForStatus(evidenceState)}>
                            {evidenceStateLabels[evidenceState]}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-mono">
                          {formatIndicatorValue(
                            item,
                            locale,
                            t("unavailableShort"),
                          )}
                        </TableCell>
                        <TableCell>
                          {formatDate(
                            item.as_of,
                            locale,
                            t("unavailableShort"),
                          )}
                        </TableCell>
                        <TableCell className="max-w-64 text-sm text-muted-foreground">
                          {item.source ?? t("unavailableShort")}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={metadataPresent ? "secondary" : "outline"}
                          >
                            {metadataPresent
                              ? t("metadataPresent")
                              : t("metadataMissing")}
                          </Badge>
                        </TableCell>
                        <TableCell className="max-w-72 text-sm text-muted-foreground">
                          {item.status === "ok"
                            ? t("indicatorStoredObservation")
                            : (item.no_data_reason ?? t("indicatorNoData"))}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </FinancialTerminalCardContent>
      </FinancialTerminalCard>

      <FinancialTerminalCard>
        <FinancialTerminalCardHeader>
          <CardTitle className="flex items-center gap-2 text-xl">
            <FileWarning className="h-5 w-5" />
            {t("sourceReadinessTitle")}
          </CardTitle>
          <CardDescription>{t("sourceReadinessDescription")}</CardDescription>
        </FinancialTerminalCardHeader>
        <FinancialTerminalCardContent className="space-y-4">
          {informationSources ? (
            <div className="grid gap-2 sm:grid-cols-4">
              {renderMetric(
                t("sourceTotal"),
                informationSources.summary?.total ?? 0,
                t("sourceTotalDesc"),
              )}
              {renderMetric(
                t("sourceConfigured"),
                informationSources.summary?.configured ?? 0,
                t("sourceConfiguredDesc"),
              )}
              {renderMetric(
                t("sourceNeedsAction"),
                informationSources.summary?.needs_action ?? 0,
                t("sourceNeedsActionDesc"),
              )}
              {renderMetric(
                t("sourceFuture"),
                informationSources.summary?.future ?? 0,
                t("sourceFutureDesc"),
              )}
            </div>
          ) : null}

          {sourceGroups.length === 0 ? (
            <EmptyState
              title={t("noSources")}
              description={t("noSourcesDesc")}
            />
          ) : (
            <div className="space-y-5">
              {sourceGroups.map((group) => (
                <section key={group.category} className="space-y-3">
                  <div>
                    <h2 className="text-lg font-semibold">{group.label}</h2>
                    <p className="text-sm text-muted-foreground">
                      {t("sourceGroupCount", { count: group.items.length })}
                    </p>
                  </div>
                  <div className="grid gap-3 xl:grid-cols-2">
                    {group.items.map((item) => {
                      const linkedNotes = getLinkedNotesForSource(
                        item.id,
                        researchSourceNotesResult.items,
                      );
                      const seedReadyNotes = linkedNotes.filter(
                        (note) =>
                          getNoteCompletenessStatus(note) === "complete",
                      );
                      return (
                        <FinancialTerminalSurface key={item.id} className="p-4">
                          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                            <div>
                              <div className="text-base font-semibold">
                                {item.label}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {item.authority ?? t("unavailableShort")}
                              </div>
                            </div>
                            <Badge variant={badgeVariantForStatus(item.status)}>
                              {sourceStatusLabels[item.status] ?? item.status}
                            </Badge>
                          </div>
                          <div className="mt-3 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
                            <div>
                              {t("sourceEvidenceCount", {
                                count: item.evidence_count ?? 0,
                              })}
                            </div>
                            <div>
                              {t("sourceLatestAsOf", {
                                date: formatDate(
                                  item.latest_as_of,
                                  locale,
                                  t("unavailableShort"),
                                ),
                              })}
                            </div>
                          </div>
                          {(item.coverage ?? []).length > 0 ? (
                            <div className="mt-3 flex flex-wrap gap-1">
                              {item.coverage?.map((coverage) => (
                                <Badge
                                  key={`${item.id}-${coverage}`}
                                  variant="outline"
                                  className="text-[10px]"
                                >
                                  {coverage}
                                </Badge>
                              ))}
                            </div>
                          ) : null}
                          <div className="mt-3 space-y-2 text-sm text-muted-foreground">
                            <p>{item.ai_usage ?? t("sourceNoAiUsage")}</p>
                            <p>
                              {item.freshness_policy ??
                                t("sourceNoFreshnessPolicy")}
                            </p>
                            <p className="font-medium text-foreground">
                              {item.next_action ?? t("sourceNoNextAction")}
                            </p>
                          </div>
                          {item.collection_note ? (
                            <div className="mt-3 space-y-1 text-sm">
                              <div className="text-xs font-semibold uppercase text-muted-foreground">
                                {t("collectionNote")}
                              </div>
                              <p className="text-muted-foreground">
                                {item.collection_note}
                              </p>
                            </div>
                          ) : null}
                          {item.citation_policy ? (
                            <div className="mt-3 space-y-1 text-sm">
                              <div className="text-xs font-semibold uppercase text-muted-foreground">
                                {t("citationPolicy")}
                              </div>
                              <p className="text-muted-foreground">
                                {item.citation_policy}
                              </p>
                            </div>
                          ) : null}
                          {(item.collection_links ?? []).length > 0 ? (
                            <div className="mt-3 space-y-2">
                              <div className="text-xs font-semibold uppercase text-muted-foreground">
                                {t("collectionLinks")}
                              </div>
                              <div className="flex flex-wrap gap-2">
                                {item.collection_links?.map((link) => (
                                  <a
                                    key={`${item.id}-${link.url}`}
                                    href={link.url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="inline-flex items-center gap-1 border px-2 py-1 text-sm text-primary hover:bg-muted hover:underline"
                                  >
                                    <span>{link.label}</span>
                                    <ExternalLink
                                      className="h-3 w-3"
                                      aria-hidden="true"
                                    />
                                  </a>
                                ))}
                              </div>
                            </div>
                          ) : null}
                          {linkedNotes.length > 0 ? (
                            <FinancialTerminalSurface className="mt-3 p-3">
                              <div className="flex flex-wrap gap-2">
                                <Badge variant="outline">
                                  {t("sourceLinkedNotebookEntries", {
                                    count: linkedNotes.length,
                                  })}
                                </Badge>
                                <Badge
                                  variant={
                                    seedReadyNotes.length > 0
                                      ? "secondary"
                                      : "outline"
                                  }
                                >
                                  {t("sourceLinkedNotebookReady", {
                                    count: seedReadyNotes.length,
                                  })}
                                </Badge>
                              </div>
                              <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-muted-foreground">
                                {linkedNotes.slice(0, 3).map((note) => (
                                  <li key={`${item.id}-${note.id}`}>
                                    {note.title}
                                  </li>
                                ))}
                              </ul>
                            </FinancialTerminalSurface>
                          ) : null}
                          {item.seed_template ? (
                            <div className="mt-4 space-y-3 border-t pt-4">
                              <div className="flex items-center gap-2 text-sm font-semibold">
                                <FileCheck2 className="h-4 w-4" />
                                {t("seedTemplate")}
                              </div>
                              <div>
                                <div className="font-medium">
                                  {item.seed_template.label}
                                </div>
                                {item.seed_template.description ? (
                                  <p className="mt-1 text-sm text-muted-foreground">
                                    {item.seed_template.description}
                                  </p>
                                ) : null}
                              </div>
                              {(item.seed_template.target_indicator_codes ?? [])
                                .length > 0 ? (
                                <div className="space-y-1">
                                  <div className="text-xs font-semibold uppercase text-muted-foreground">
                                    {t("templateTargets")}
                                  </div>
                                  <div className="flex flex-wrap gap-1">
                                    {item.seed_template.target_indicator_codes?.map(
                                      (code) => (
                                        <Badge
                                          key={`${item.id}-${code}`}
                                          variant="outline"
                                          className="text-[10px]"
                                        >
                                          {code}
                                        </Badge>
                                      ),
                                    )}
                                  </div>
                                </div>
                              ) : null}
                              {(item.seed_template.required_fields ?? [])
                                .length > 0 ? (
                                <div className="space-y-1 text-sm">
                                  <div className="text-xs font-semibold uppercase text-muted-foreground">
                                    {t("templateRequiredFields")}
                                  </div>
                                  <p className="text-muted-foreground">
                                    {item.seed_template.required_fields?.join(
                                      ", ",
                                    )}
                                  </p>
                                </div>
                              ) : null}
                              {item.seed_template.import_command ? (
                                <div className="space-y-1">
                                  <div className="text-xs font-semibold uppercase text-muted-foreground">
                                    {t("templateImportCommand")}
                                  </div>
                                  <code className="block break-all border bg-muted/40 p-2 font-mono text-xs">
                                    {item.seed_template.import_command}
                                  </code>
                                </div>
                              ) : null}
                              {item.seed_template.json_template ? (
                                <div className="space-y-1">
                                  <div className="text-xs font-semibold uppercase text-muted-foreground">
                                    {t("templateJson")}
                                  </div>
                                  <pre className="max-h-48 overflow-auto border bg-muted/30 p-2 text-xs">
                                    {JSON.stringify(
                                      item.seed_template.json_template,
                                      null,
                                      2,
                                    )}
                                  </pre>
                                </div>
                              ) : null}
                              {item.seed_template.csv_header ||
                              item.seed_template.csv_example_rows ? (
                                <div className="space-y-1">
                                  <div className="text-xs font-semibold uppercase text-muted-foreground">
                                    {t("templateCsv")}
                                  </div>
                                  <pre className="max-h-32 overflow-auto border bg-muted/30 p-2 text-xs">
                                    {[
                                      item.seed_template.csv_header?.join(","),
                                      ...(item.seed_template.csv_example_rows ??
                                        []),
                                    ]
                                      .filter(Boolean)
                                      .join("\n")}
                                  </pre>
                                </div>
                              ) : null}
                              {(item.seed_template.review_checklist ?? [])
                                .length > 0 ? (
                                <div className="space-y-1">
                                  <div className="text-xs font-semibold uppercase text-muted-foreground">
                                    {t("templateChecklist")}
                                  </div>
                                  <ul className="list-disc space-y-1 pl-4 text-sm text-muted-foreground">
                                    {item.seed_template.review_checklist?.map(
                                      (checklistItem) => (
                                        <li
                                          key={`${item.id}-${checklistItem.id}`}
                                        >
                                          <span className="font-medium text-foreground">
                                            {checklistItem.label}
                                          </span>
                                          {checklistItem.why ? (
                                            <span> {checklistItem.why}</span>
                                          ) : null}
                                        </li>
                                      ),
                                    )}
                                  </ul>
                                </div>
                              ) : null}
                              {(item.seed_template.warnings ?? []).length >
                              0 ? (
                                <div className="space-y-1">
                                  <div className="text-xs font-semibold uppercase text-muted-foreground">
                                    {t("templateWarnings")}
                                  </div>
                                  <ul className="list-disc space-y-1 pl-4 text-sm text-muted-foreground">
                                    {item.seed_template.warnings?.map(
                                      (warning) => (
                                        <li key={`${item.id}-${warning}`}>
                                          {warning}
                                        </li>
                                      ),
                                    )}
                                  </ul>
                                </div>
                              ) : null}
                              {item.seed_template.citation_boundary ? (
                                <p className="border-l-2 pl-3 text-sm text-muted-foreground">
                                  {item.seed_template.citation_boundary}
                                </p>
                              ) : null}
                            </div>
                          ) : null}
                        </FinancialTerminalSurface>
                      );
                    })}
                  </div>
                </section>
              ))}
            </div>
          )}
        </FinancialTerminalCardContent>
      </FinancialTerminalCard>

      <section className="space-y-3">
        <div>
          <h2 className="text-xl font-semibold">{t("advancedToolsTitle")}</h2>
          <p className="text-sm text-muted-foreground">
            {t("advancedToolsDescription")}
          </p>
        </div>
        <EvidenceSeedImportReview
          labels={buildSeedImportLabels(seedImportT)}
        />
      </section>
        </div>
      </details>

      <FinancialTerminalCard>
        <FinancialTerminalCardHeader>
          <CardTitle>{t("citationBoundaryTitle")}</CardTitle>
          <CardDescription>{t("citationBoundaryDescription")}</CardDescription>
        </FinancialTerminalCardHeader>
        <FinancialTerminalCardContent>
          <ul className="grid gap-2 text-sm text-muted-foreground md:grid-cols-3">
            <li className="rounded-md border border-border/70 bg-background/60 p-3">
              {t("citationBoundaryLocalEvidence")}
            </li>
            <li className="rounded-md border border-border/70 bg-background/60 p-3">
              {t("citationBoundaryGuidanceOnly")}
            </li>
            <li className="rounded-md border border-border/70 bg-background/60 p-3">
              {t("citationBoundaryNoTradingAdvice")}
            </li>
          </ul>
        </FinancialTerminalCardContent>
      </FinancialTerminalCard>
        </div>
      </details>
    </div>
  );
}
