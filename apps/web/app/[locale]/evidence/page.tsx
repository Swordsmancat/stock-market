import { getTranslations } from "next-intl/server";
import { Database, ExternalLink, FileCheck2, FileWarning, SearchCheck, ShieldCheck } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import {
  EvidenceSeedImportReview,
  type EvidenceSeedImportReviewLabels,
} from "@/components/evidence-seed-import-review";
import { ErrorState } from "@/components/error-state";
import {
  ResearchSourceNotebook,
  type ResearchSourceNotebookLabels,
  type ResearchSourceNote,
  type ResearchSourceTargetOption,
} from "@/components/research-source-notebook";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
  type DashboardBriefPayload,
  type InformationSourceItem,
  type InformationSourcesPayload,
  type MarketOverviewIndicatorItem,
  type MarketOverviewPayload,
} from "@/lib/market-overview-payload";
import { getPlatformSettings } from "@/lib/platform-settings-store";
import { Link } from "@/src/i18n/routing";

type EvidenceCenterPageProps = {
  params?: Promise<{ locale: string }>;
  searchParams?: Promise<{ provider?: string }>;
};

type MarketOverviewLoadResult =
  | { status: "loaded"; payload: MarketOverviewPayload }
  | { status: "failed" };

type ResearchSourceNotesLoadResult =
  | { status: "loaded"; items: ResearchSourceNote[] }
  | { status: "failed"; items: [] };

type IndicatorEvidenceState =
  | "ai_citable"
  | "needs_adapter"
  | "needs_manual_seed"
  | "no_local_evidence"
  | "future"
  | "needs_review";

const FALLBACK_LOCALE = "en-US";
const AUDIT_SOURCE_COMPONENT_KEYS = ["source_url", "source_series_id", "source_document", "source_name"];
const AUDIT_METHOD_COMPONENT_KEYS = ["methodology", "calculation", "notes", "review_note"];

async function fetchMarketOverview(provider: string): Promise<MarketOverviewLoadResult> {
  try {
    const response = await backendFetch(withProviderQuery("/dashboard/market-overview", provider), {
      cache: "no-store",
    });
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

function formatDate(value: string | null | undefined, locale: string, unavailableLabel: string): string {
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

function hasNonEmptyComponent(components: Record<string, unknown> | undefined, keys: string[]): boolean {
  if (!components) {
    return false;
  }

  return keys.some((key) => {
    const value = components[key];
    return value !== undefined && value !== null && String(value).trim().length > 0;
  });
}

function hasAuditMetadata(item: MarketOverviewIndicatorItem): boolean {
  return (
    hasNonEmptyComponent(item.components, AUDIT_SOURCE_COMPONENT_KEYS) &&
    hasNonEmptyComponent(item.components, AUDIT_METHOD_COMPONENT_KEYS)
  );
}

function isIndicatorCitable(item: MarketOverviewIndicatorItem): boolean {
  return item.status === "ok" && typeof item.value === "number" && Boolean(item.as_of) && Boolean(item.source);
}

function sourceMentionsIndicator(source: InformationSourceItem, code: string): boolean {
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

function getIndicatorItems(payload: MarketOverviewPayload): MarketOverviewIndicatorItem[] {
  return payload.macro_indicators?.items ?? payload.valuation_indicators?.items ?? [];
}

function getSourceGroups(informationSources: InformationSourcesPayload | null) {
  const groupsWithItems = (informationSources?.groups ?? []).filter((group) => group.items.length > 0);
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

function buildNotebookSourceTargets(informationSources: InformationSourcesPayload | null): ResearchSourceTargetOption[] {
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
          item.seed_template?.target_indicator_codes && item.seed_template.target_indicator_codes.length > 0
            ? item.seed_template.target_indicator_codes
            : item.coverage ?? [],
      },
    ];
  });
}

function getNoteMetadata(note: ResearchSourceNote): Record<string, unknown> {
  return note.metadata && typeof note.metadata === "object" ? note.metadata : {};
}

function getLinkedNotesForSource(sourceId: string, notes: ResearchSourceNote[]): ResearchSourceNote[] {
  return notes.filter((note) => getNoteMetadata(note).source_id === sourceId);
}

function getNoteCompletenessStatus(note: ResearchSourceNote): string {
  const completeness = getNoteMetadata(note).completeness;
  if (!completeness || typeof completeness !== "object" || !("status" in completeness)) {
    return "missing";
  }
  const status = completeness.status;
  return typeof status === "string" ? status : "missing";
}

function countCitableIndicators(items: MarketOverviewIndicatorItem[]): number {
  return items.filter(isIndicatorCitable).length;
}

function countMissingIndicators(items: MarketOverviewIndicatorItem[]): number {
  return items.filter((item) => !isIndicatorCitable(item)).length;
}

function badgeVariantForStatus(status: string): "secondary" | "outline" | "destructive" {
  if (status === "ok" || status === "configured" || status === "ai_citable") {
    return "secondary";
  }
  if (status === "no_local_evidence" || status === "no_data") {
    return "destructive";
  }
  return "outline";
}

function renderMetric(label: string, value: string | number, description: string) {
  return (
    <div className="border bg-background p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 font-mono text-2xl font-semibold">{value}</div>
      <div className="mt-1 text-xs text-muted-foreground">{description}</div>
    </div>
  );
}

function renderBriefSectionList(brief: DashboardBriefPayload) {
  return brief.sections.map((section) => (
    <div key={section.id} className="border bg-background p-3">
      <div className="text-sm font-semibold">{section.title}</div>
      <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-muted-foreground">
        {section.items.map((item, index) => (
          <li key={`${section.id}-${index}`}>{item}</li>
        ))}
      </ul>
    </div>
  ));
}

function buildSeedImportLabels(t: Awaited<ReturnType<typeof getTranslations>>): EvidenceSeedImportReviewLabels {
  return {
    title: t("title"),
    description: t("description"),
    fileLabel: t("fileLabel"),
    fileButton: t("fileButton"),
    selectedFile: t("selectedFile"),
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

function buildNotebookLabels(t: Awaited<ReturnType<typeof getTranslations>>): ResearchSourceNotebookLabels {
  return {
    title: t("title"),
    description: t("description"),
    selectedFile: t("selectedFile"),
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
    citationId: t("citationId"),
    sourceLink: t("sourceLink"),
    linkedSourceBadge: t("linkedSourceBadge"),
    targetIndicatorsBadge: t("targetIndicatorsBadge"),
    componentRoleBadge: t("componentRoleBadge"),
    reviewChecklistTitle: t("reviewChecklistTitle"),
    completenessSummary: t("completenessSummary"),
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

export default async function EvidenceCenterPage({
  params = Promise.resolve({ locale: "en" }),
  searchParams = Promise.resolve({}),
}: EvidenceCenterPageProps = {}) {
  const [{ locale: requestedLocale }, query, platformSettings, t, seedImportT, notebookT] = await Promise.all([
    params,
    searchParams,
    getPlatformSettings(),
    getTranslations("EvidenceCenter"),
    getTranslations("EvidenceSeedImport"),
    getTranslations("ResearchSourceNotebook"),
  ]);
  const locale = getSafeLocale(requestedLocale);
  const provider = query.provider?.trim() || platformSettings.market_data_provider;
  const [marketOverviewResult, researchSourceNotesResult] = await Promise.all([
    fetchMarketOverview(provider),
    fetchResearchSourceNotes(),
  ]);

  if (marketOverviewResult.status === "failed") {
    return (
      <div className="space-y-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
            <p className="text-muted-foreground">{t("description")}</p>
          </div>
          <Button variant="outline" asChild>
            <Link href="/settings">{t("openSettings")}</Link>
          </Button>
        </div>
        <ErrorState title={t("loadFailedTitle")} description={t("loadFailedDescription")} />
      </div>
    );
  }

  const payload = marketOverviewResult.payload;
  const indicators = getIndicatorItems(payload);
  const dashboardBrief = payload.dashboard_brief ?? null;
  const informationSources = payload.information_sources ?? null;
  const sourceGroups = getSourceGroups(informationSources);
  const sourceTargetOptions = buildNotebookSourceTargets(informationSources);
  const citableIndicatorCount = countCitableIndicators(indicators);
  const missingIndicatorCount = countMissingIndicators(indicators);
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
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="max-w-3xl">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">{t("badge")}</Badge>
            <Badge variant="outline">{t("activeProvider", { provider })}</Badge>
            <Badge variant="outline">
              {t("generatedAt", { date: formatDate(payload.generated_at, locale, t("unavailableShort")) })}
            </Badge>
          </div>
          <h1 className="mt-3 text-3xl font-bold tracking-tight">{t("title")}</h1>
          <p className="mt-1 text-muted-foreground">{t("description")}</p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Button variant="outline" asChild>
            <Link href="/reports">{t("openReports")}</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href="/task-runs">{t("openTaskRuns")}</Link>
          </Button>
        </div>
      </div>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {renderMetric(t("metricIndicators"), indicators.length, t("metricIndicatorsDesc"))}
        {renderMetric(t("metricCitable"), citableIndicatorCount, t("metricCitableDesc"))}
        {renderMetric(t("metricMissing"), missingIndicatorCount, t("metricMissingDesc"))}
        {renderMetric(
          t("metricSourcesNeedAction"),
          informationSources?.summary?.needs_action ?? 0,
          t("metricSourcesNeedActionDesc"),
        )}
      </section>

      <EvidenceSeedImportReview labels={buildSeedImportLabels(seedImportT)} />

      <ResearchSourceNotebook
        labels={buildNotebookLabels(notebookT)}
        initialNotes={researchSourceNotesResult.items}
        sourceTargets={sourceTargetOptions}
        loadFailed={researchSourceNotesResult.status === "failed"}
      />

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(22rem,0.85fr)]">
        <Card className="border-primary/20">
          <CardHeader>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={dashboardBrief?.status === "ok" ? "secondary" : "outline"}>
                {dashboardBrief?.status ?? t("unavailableShort")}
              </Badge>
              {dashboardBrief ? (
                <Badge variant="outline">
                  {formatDate(dashboardBrief.generated_at, locale, t("unavailableShort"))}
                </Badge>
              ) : null}
            </div>
            <CardTitle className="flex items-center gap-2 text-xl">
              <SearchCheck className="h-5 w-5" />
              {t("briefTitle")}
            </CardTitle>
            <CardDescription>{t("briefDescription")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {dashboardBrief?.narrative?.answer_markdown ? (
              <div className="border border-primary/20 bg-primary/5 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <div className="text-sm font-semibold">{t("briefNarrative")}</div>
                  <Badge
                    variant={dashboardBrief.narrative.model.used_llm ? "secondary" : "outline"}
                    className="text-[10px]"
                  >
                    {dashboardBrief.narrative.model.used_llm ? t("modelGenerated") : t("modelFallback")}
                  </Badge>
                  {dashboardBrief.narrative.model.name ? (
                    <Badge variant="outline" className="text-[10px]">
                      {t("modelName", { name: dashboardBrief.narrative.model.name })}
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
              </div>
            ) : (
              <EmptyState title={t("briefNarrativeUnavailable")} description={t("briefNarrativeUnavailableDesc")} />
            )}

            {dashboardBrief?.narrative?.context?.source_mix ? (
              <div className="grid gap-2 text-sm sm:grid-cols-4">
                <div className="border p-2">
                  {t("macroEvidence", {
                    count: dashboardBrief.narrative.context.source_mix.macro_citations ?? 0,
                  })}
                </div>
                <div className="border p-2">
                  {t("reportEvidence", {
                    count: dashboardBrief.narrative.context.source_mix.report_citations ?? 0,
                  })}
                </div>
                <div className="border p-2">
                  {t("newsEvidence", {
                    count: dashboardBrief.narrative.context.source_mix.news_citations ?? 0,
                  })}
                </div>
                <div className="border p-2">
                  {t("sourceGaps", {
                    count: dashboardBrief.narrative.context.source_mix.information_source_gaps ?? 0,
                  })}
                </div>
              </div>
            ) : null}

            {dashboardBrief ? (
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                {renderBriefSectionList(dashboardBrief)}
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl">
              <ShieldCheck className="h-5 w-5" />
              {t("briefEvidenceTitle")}
            </CardTitle>
            <CardDescription>{t("briefEvidenceDescription")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {(dashboardBrief?.citations?.length ?? 0) > 0 ? (
              <div className="space-y-2">
                <div className="text-sm font-semibold">{t("citationsTitle")}</div>
                <div className="flex flex-wrap gap-2">
                  {dashboardBrief?.citations?.map((citation) => (
                    <Badge key={citation.id} variant="outline">
                      {citation.label}
                    </Badge>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">{t("noCitations")}</p>
            )}

            {(dashboardBrief?.diagnostics?.length ?? 0) > 0 ? (
              <div className="border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
                <div className="font-semibold">{t("diagnosticsTitle")}</div>
                <ul className="mt-2 list-disc space-y-1 pl-4">
                  {dashboardBrief?.diagnostics?.map((diagnostic, index) => (
                    <li key={`${diagnostic.source ?? "diagnostic"}-${diagnostic.code ?? index}`}>
                      {diagnostic.code ? `${diagnostic.code}: ` : null}
                      {diagnostic.message ?? diagnostic.status ?? t("unavailableShort")}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {dashboardBrief?.safety ? (
              <div className="space-y-2 text-sm">
                <div className="font-semibold">{t("safetyTitle")}</div>
                <div className="flex flex-wrap gap-2">
                  {dashboardBrief.safety.not_investment_advice ? (
                    <Badge variant="secondary">{t("safetyNotAdvice")}</Badge>
                  ) : null}
                  {dashboardBrief.safety.no_buy_sell_hold ? (
                    <Badge variant="secondary">{t("safetyNoTradingInstruction")}</Badge>
                  ) : null}
                  {dashboardBrief.safety.no_fabricated_macro_data ? (
                    <Badge variant="secondary">{t("safetyNoFabricatedData")}</Badge>
                  ) : null}
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-xl">
            <Database className="h-5 w-5" />
            {t("indicatorTableTitle")}
          </CardTitle>
          <CardDescription>{t("indicatorTableDescription")}</CardDescription>
        </CardHeader>
        <CardContent>
          {indicators.length === 0 ? (
            <EmptyState title={t("noIndicators")} description={t("noIndicatorsDesc")} />
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
                    const evidenceState = getIndicatorEvidenceState(item, informationSources);
                    const metadataPresent = hasAuditMetadata(item);
                    return (
                      <TableRow key={item.code}>
                        <TableCell className="min-w-56">
                          <div className="font-medium">{item.name}</div>
                          <div className="font-mono text-xs text-muted-foreground">{item.code}</div>
                          <div className="mt-1 text-xs text-muted-foreground">
                            {[item.region, item.category].filter(Boolean).join(" / ") || t("unavailableShort")}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={badgeVariantForStatus(evidenceState)}>
                            {evidenceStateLabels[evidenceState]}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-mono">
                          {formatIndicatorValue(item, locale, t("unavailableShort"))}
                        </TableCell>
                        <TableCell>{formatDate(item.as_of, locale, t("unavailableShort"))}</TableCell>
                        <TableCell className="max-w-64 text-sm text-muted-foreground">
                          {item.source ?? t("unavailableShort")}
                        </TableCell>
                        <TableCell>
                          <Badge variant={metadataPresent ? "secondary" : "outline"}>
                            {metadataPresent ? t("metadataPresent") : t("metadataMissing")}
                          </Badge>
                        </TableCell>
                        <TableCell className="max-w-72 text-sm text-muted-foreground">
                          {item.status === "ok"
                            ? t("indicatorStoredObservation")
                            : item.no_data_reason ?? t("indicatorNoData")}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-xl">
            <FileWarning className="h-5 w-5" />
            {t("sourceReadinessTitle")}
          </CardTitle>
          <CardDescription>{t("sourceReadinessDescription")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
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
              {renderMetric(t("sourceFuture"), informationSources.summary?.future ?? 0, t("sourceFutureDesc"))}
            </div>
          ) : null}

          {sourceGroups.length === 0 ? (
            <EmptyState title={t("noSources")} description={t("noSourcesDesc")} />
          ) : (
            <div className="space-y-5">
              {sourceGroups.map((group) => (
                <section key={group.category} className="space-y-3">
                  <div>
                    <h2 className="text-lg font-semibold">{group.label}</h2>
                    <p className="text-sm text-muted-foreground">{t("sourceGroupCount", { count: group.items.length })}</p>
                  </div>
                  <div className="grid gap-3 xl:grid-cols-2">
                    {group.items.map((item) => {
                      const linkedNotes = getLinkedNotesForSource(item.id, researchSourceNotesResult.items);
                      const seedReadyNotes = linkedNotes.filter(
                        (note) => getNoteCompletenessStatus(note) === "complete",
                      );
                      return (
                      <div key={item.id} className="border bg-background p-4">
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                          <div>
                            <div className="text-base font-semibold">{item.label}</div>
                            <div className="text-xs text-muted-foreground">{item.authority ?? t("unavailableShort")}</div>
                          </div>
                          <Badge variant={badgeVariantForStatus(item.status)}>
                            {sourceStatusLabels[item.status] ?? item.status}
                          </Badge>
                        </div>
                        <div className="mt-3 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
                          <div>{t("sourceEvidenceCount", { count: item.evidence_count ?? 0 })}</div>
                          <div>
                            {t("sourceLatestAsOf", {
                              date: formatDate(item.latest_as_of, locale, t("unavailableShort")),
                            })}
                          </div>
                        </div>
                        {(item.coverage ?? []).length > 0 ? (
                          <div className="mt-3 flex flex-wrap gap-1">
                            {item.coverage?.map((coverage) => (
                              <Badge key={`${item.id}-${coverage}`} variant="outline" className="text-[10px]">
                                {coverage}
                              </Badge>
                            ))}
                          </div>
                        ) : null}
                        <div className="mt-3 space-y-2 text-sm text-muted-foreground">
                          <p>{item.ai_usage ?? t("sourceNoAiUsage")}</p>
                          <p>{item.freshness_policy ?? t("sourceNoFreshnessPolicy")}</p>
                          <p className="font-medium text-foreground">{item.next_action ?? t("sourceNoNextAction")}</p>
                        </div>
                        {item.collection_note ? (
                          <div className="mt-3 space-y-1 text-sm">
                            <div className="text-xs font-semibold uppercase text-muted-foreground">
                              {t("collectionNote")}
                            </div>
                            <p className="text-muted-foreground">{item.collection_note}</p>
                          </div>
                        ) : null}
                        {item.citation_policy ? (
                          <div className="mt-3 space-y-1 text-sm">
                            <div className="text-xs font-semibold uppercase text-muted-foreground">
                              {t("citationPolicy")}
                            </div>
                            <p className="text-muted-foreground">{item.citation_policy}</p>
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
                                  <ExternalLink className="h-3 w-3" aria-hidden="true" />
                                </a>
                              ))}
                            </div>
                          </div>
                        ) : null}
                        {linkedNotes.length > 0 ? (
                          <div className="mt-3 border bg-muted/20 p-3">
                            <div className="flex flex-wrap gap-2">
                              <Badge variant="outline">
                                {t("sourceLinkedNotebookEntries", { count: linkedNotes.length })}
                              </Badge>
                              <Badge variant={seedReadyNotes.length > 0 ? "secondary" : "outline"}>
                                {t("sourceLinkedNotebookReady", { count: seedReadyNotes.length })}
                              </Badge>
                            </div>
                            <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-muted-foreground">
                              {linkedNotes.slice(0, 3).map((note) => (
                                <li key={`${item.id}-${note.id}`}>{note.title}</li>
                              ))}
                            </ul>
                          </div>
                        ) : null}
                        {item.seed_template ? (
                          <div className="mt-4 space-y-3 border-t pt-4">
                            <div className="flex items-center gap-2 text-sm font-semibold">
                              <FileCheck2 className="h-4 w-4" />
                              {t("seedTemplate")}
                            </div>
                            <div>
                              <div className="font-medium">{item.seed_template.label}</div>
                              {item.seed_template.description ? (
                                <p className="mt-1 text-sm text-muted-foreground">{item.seed_template.description}</p>
                              ) : null}
                            </div>
                            {(item.seed_template.target_indicator_codes ?? []).length > 0 ? (
                              <div className="space-y-1">
                                <div className="text-xs font-semibold uppercase text-muted-foreground">
                                  {t("templateTargets")}
                                </div>
                                <div className="flex flex-wrap gap-1">
                                  {item.seed_template.target_indicator_codes?.map((code) => (
                                    <Badge key={`${item.id}-${code}`} variant="outline" className="text-[10px]">
                                      {code}
                                    </Badge>
                                  ))}
                                </div>
                              </div>
                            ) : null}
                            {(item.seed_template.required_fields ?? []).length > 0 ? (
                              <div className="space-y-1 text-sm">
                                <div className="text-xs font-semibold uppercase text-muted-foreground">
                                  {t("templateRequiredFields")}
                                </div>
                                <p className="text-muted-foreground">
                                  {item.seed_template.required_fields?.join(", ")}
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
                                  {JSON.stringify(item.seed_template.json_template, null, 2)}
                                </pre>
                              </div>
                            ) : null}
                            {item.seed_template.csv_header || item.seed_template.csv_example_rows ? (
                              <div className="space-y-1">
                                <div className="text-xs font-semibold uppercase text-muted-foreground">
                                  {t("templateCsv")}
                                </div>
                                <pre className="max-h-32 overflow-auto border bg-muted/30 p-2 text-xs">
                                  {[
                                    item.seed_template.csv_header?.join(","),
                                    ...(item.seed_template.csv_example_rows ?? []),
                                  ]
                                    .filter(Boolean)
                                    .join("\n")}
                                </pre>
                              </div>
                            ) : null}
                            {(item.seed_template.review_checklist ?? []).length > 0 ? (
                              <div className="space-y-1">
                                <div className="text-xs font-semibold uppercase text-muted-foreground">
                                  {t("templateChecklist")}
                                </div>
                                <ul className="list-disc space-y-1 pl-4 text-sm text-muted-foreground">
                                  {item.seed_template.review_checklist?.map((checklistItem) => (
                                    <li key={`${item.id}-${checklistItem.id}`}>
                                      <span className="font-medium text-foreground">{checklistItem.label}</span>
                                      {checklistItem.why ? <span> {checklistItem.why}</span> : null}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            ) : null}
                            {(item.seed_template.warnings ?? []).length > 0 ? (
                              <div className="space-y-1">
                                <div className="text-xs font-semibold uppercase text-muted-foreground">
                                  {t("templateWarnings")}
                                </div>
                                <ul className="list-disc space-y-1 pl-4 text-sm text-muted-foreground">
                                  {item.seed_template.warnings?.map((warning) => (
                                    <li key={`${item.id}-${warning}`}>{warning}</li>
                                  ))}
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
                      </div>
                      );
                    })}
                  </div>
                </section>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="border-primary/20">
        <CardHeader>
          <CardTitle>{t("citationBoundaryTitle")}</CardTitle>
          <CardDescription>{t("citationBoundaryDescription")}</CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="grid gap-2 text-sm text-muted-foreground md:grid-cols-3">
            <li className="border p-3">{t("citationBoundaryLocalEvidence")}</li>
            <li className="border p-3">{t("citationBoundaryGuidanceOnly")}</li>
            <li className="border p-3">{t("citationBoundaryNoTradingAdvice")}</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
