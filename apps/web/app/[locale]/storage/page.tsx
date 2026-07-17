import type { LucideIcon } from "lucide-react";
import {
  Activity,
  Boxes,
  BrainCircuit,
  CandlestickChart,
  Database,
  FileChartColumn,
  Globe2,
  Landmark,
  Newspaper,
  UserRoundCog,
} from "lucide-react";
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
import {
  formatStorageBytes,
  formatStorageCount,
  isStorageOverviewPayload,
  type StorageDomainCode,
  type StorageOverviewPayload,
} from "@/lib/storage-overview";

type LoadResult =
  | { status: "loaded"; payload: StorageOverviewPayload }
  | { status: "failed"; payload: null };

const DOMAIN_PRESENTATION = {
  reference_data: { labelKey: "domainReferenceData", icon: Landmark },
  market_prices: { labelKey: "domainMarketPrices", icon: CandlestickChart },
  technical_analysis: { labelKey: "domainTechnicalAnalysis", icon: Activity },
  fundamentals: { labelKey: "domainFundamentals", icon: FileChartColumn },
  macro_economy: { labelKey: "domainMacroEconomy", icon: Globe2 },
  market_structure: { labelKey: "domainMarketStructure", icon: Boxes },
  news_disclosures: { labelKey: "domainNewsDisclosures", icon: Newspaper },
  research_outputs: { labelKey: "domainResearchOutputs", icon: BrainCircuit },
  personal_operations: { labelKey: "domainPersonalOperations", icon: UserRoundCog },
  other: { labelKey: "domainOther", icon: Database },
} as const satisfies Record<StorageDomainCode, { labelKey: string; icon: LucideIcon }>;

function getDomainPresentation(code: string) {
  return DOMAIN_PRESENTATION[code as StorageDomainCode] ?? DOMAIN_PRESENTATION.other;
}

async function loadStorageOverview(): Promise<LoadResult> {
  try {
    const response = await backendFetch("/storage/overview", { cache: "no-store" });
    if (!response.ok) return { status: "failed", payload: null };
    const payload: unknown = await response.json();
    if (!isStorageOverviewPayload(payload)) {
      return { status: "failed", payload: null };
    }
    return { status: "loaded", payload };
  } catch {
    return { status: "failed", payload: null };
  }
}

export default async function StorageOverviewPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const [{ locale }, t, result] = await Promise.all([
    params,
    getTranslations("StorageOverview"),
    loadStorageOverview(),
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
        <ErrorState
          title={t("loadFailedTitle")}
          description={t("loadFailedDescription")}
        />
      </div>
    );
  }

  const { payload } = result;
  const countLabel = payload.row_count_kind === "estimated" ? t("estimated") : t("exact");
  const collectedAt = new Date(payload.collected_at);
  const collectedAtLabel = Number.isNaN(collectedAt.valueOf())
    ? t("unavailable")
    : new Intl.DateTimeFormat(locale, {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: "Asia/Shanghai",
      }).format(collectedAt);
  const formatBytes = (value: number | null) =>
    formatStorageBytes(value, locale) ?? t("unavailable");

  return (
    <div className="space-y-6">
      <FinancialPageHeader
        title={t("title")}
        description={t("description")}
        badges={[
          { label: payload.engine },
          { label: t("readOnlyBadge"), variant: "secondary" },
          { label: countLabel, variant: "outline" },
        ]}
        metrics={[
          {
            label: t("metricTables"),
            value: payload.summary.table_count,
            description: t("metricTablesDescription"),
          },
          {
            label: t("metricRecords"),
            value: formatStorageCount(payload.summary.estimated_rows, locale),
            description: t("metricRecordsDescription", { kind: countLabel }),
          },
          {
            label: t("metricDataSize"),
            value: formatBytes(payload.summary.data_bytes),
            description: t("metricDataSizeDescription"),
          },
          {
            label: t("metricTotalSize"),
            value: formatBytes(payload.summary.total_bytes),
            description: t("metricTotalSizeDescription", {
              indexes: formatBytes(payload.summary.index_bytes),
            }),
          },
        ]}
      />

      {payload.domains.length === 0 ? (
        <FinancialTerminalCard>
          <EmptyState title={t("emptyTitle")} description={t("emptyDescription")} />
        </FinancialTerminalCard>
      ) : (
        <>
          <section aria-labelledby="storage-domains-heading" className="space-y-3">
            <div>
              <h2 id="storage-domains-heading" className="text-base font-semibold">
                {t("domainsTitle")}
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">{t("domainsDescription")}</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-5">
              {payload.domains.map((domain) => {
                const presentation = getDomainPresentation(domain.code);
                const Icon = presentation.icon;
                return (
                  <FinancialTerminalSurface
                    key={domain.code}
                    className="min-w-0 space-y-3 p-3 sm:p-4"
                  >
                    <div className="flex min-w-0 items-center gap-2">
                      <Icon aria-hidden="true" className="h-4 w-4 shrink-0 text-primary" />
                      <h3 className="truncate text-sm font-medium">
                        {t(presentation.labelKey)}
                      </h3>
                    </div>
                    <div>
                      <div className="font-mono text-2xl font-semibold tabular-nums">
                        {formatStorageCount(domain.estimated_rows, locale)}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {t("records", { kind: countLabel })}
                      </div>
                    </div>
                    <div className="flex items-center justify-between gap-3 border-t border-border/60 pt-2 text-xs text-muted-foreground">
                      <span>{t("tables", { count: domain.table_count })}</span>
                      <span className="font-mono tabular-nums">{formatBytes(domain.total_bytes)}</span>
                    </div>
                  </FinancialTerminalSurface>
                );
              })}
            </div>
          </section>

          <FinancialTerminalCard>
            <FinancialTerminalCardHeader>
              <CardTitle id="storage-inventory-heading">{t("inventoryTitle")}</CardTitle>
              <CardDescription>
                {t("inventoryDescription", { collectedAt: collectedAtLabel })}
              </CardDescription>
            </FinancialTerminalCardHeader>
            <FinancialTerminalCardContent className="p-0">
              <Table
                className="min-w-[760px]"
                containerProps={{
                  role: "region",
                  "aria-labelledby": "storage-inventory-heading",
                  tabIndex: 0,
                }}
                containerClassName="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("columnDomain")}</TableHead>
                    <TableHead>{t("columnTable")}</TableHead>
                    <TableHead className="text-right">{t("columnRecords")}</TableHead>
                    <TableHead className="text-right">{t("columnDataSize")}</TableHead>
                    <TableHead className="text-right">{t("columnIndexSize")}</TableHead>
                    <TableHead className="text-right">{t("columnTotalSize")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {payload.domains.flatMap((domain) =>
                    domain.tables.map((table) => (
                      <TableRow key={`${domain.code}:${table.name}`}>
                        <TableCell className="text-muted-foreground">
                          {t(getDomainPresentation(domain.code).labelKey)}
                        </TableCell>
                        <TableCell className="font-mono text-xs">{table.name}</TableCell>
                        <TableCell className="text-right font-mono tabular-nums">
                          {new Intl.NumberFormat(locale).format(table.estimated_rows)}
                        </TableCell>
                        <TableCell className="text-right font-mono tabular-nums">
                          {formatBytes(table.data_bytes)}
                        </TableCell>
                        <TableCell className="text-right font-mono tabular-nums">
                          {formatBytes(table.index_bytes)}
                        </TableCell>
                        <TableCell className="text-right font-mono tabular-nums">
                          {formatBytes(table.total_bytes)}
                        </TableCell>
                      </TableRow>
                    )),
                  )}
                </TableBody>
              </Table>
            </FinancialTerminalCardContent>
          </FinancialTerminalCard>
        </>
      )}
    </div>
  );
}
