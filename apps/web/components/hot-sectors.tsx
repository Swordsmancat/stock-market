"use client";

import { TrendingUp, TrendingDown, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { useTranslations } from "next-intl";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useMarketColorsContext } from "@/context/market-colors-context";

type HotSectorsStatus = "ok" | "degraded" | "unavailable";
type HotSectorsDataMode = "live" | "delayed" | "demo" | "mock" | "none";
type FlowDirection = "inflow" | "outflow" | "flat" | "unknown";

type HotSectorConstituent = {
  symbol: string;
  name: string;
  change_percent?: number | null;
  weight?: number | null;
  net_flow_amount?: number | null;
};

type HotSectorFlowDefinition = {
  metric?: string | null;
  window?: string | null;
  currency?: string | null;
  unit?: string | null;
  methodology?: string | null;
};

type HotSectorBreadth = {
  status?: string | null;
  advancers?: number | null;
  decliners?: number | null;
  unchanged?: number | null;
  total?: number | null;
  advance_decline_ratio?: number | null;
  reason?: string | null;
};

type HotSectorContributionEntry = {
  symbol?: string | null;
  name?: string | null;
  value?: number | null;
  label?: string | null;
};

type HotSectorConstituentContribution = {
  status?: string | null;
  metric?: string | null;
  top_positive?: HotSectorContributionEntry[];
  top_negative?: HotSectorContributionEntry[];
  reason?: string | null;
};

type HotSectorTaxonomy = {
  status?: string | null;
  provider_taxonomy?: string | null;
  taxonomy_version?: string | null;
  normalized_sector_id?: string | null;
};

type HotSectorHistory = {
  status?: string | null;
  reason?: string | null;
  snapshot_count?: number | null;
};

interface Sector {
  sector_id?: string;
  name: string;
  name_en: string;
  market?: string | null;
  rank?: number | null;
  change_percent?: number | null;
  fund_flow?: string | null;
  fund_flow_amount?: number | null;
  flow_direction?: FlowDirection | string | null;
  net_flow_amount?: number | null;
  net_flow_currency?: string | null;
  net_flow_unit?: string | null;
  flow_definition?: string | null;
  leader_symbol?: string | null;
  leader_name?: string | null;
  leader_change_percent?: number | null;
  leader?: HotSectorConstituent | null;
  symbols_count: number;
  top_constituents?: HotSectorConstituent[];
  breadth?: HotSectorBreadth | null;
  constituent_contribution?: HotSectorConstituentContribution | null;
  taxonomy?: HotSectorTaxonomy | null;
  history?: HotSectorHistory | null;
  as_of?: string | null;
  provider?: string | null;
  is_verified?: boolean;
}

interface HotSectorsProps {
  sectors: Sector[];
  status?: HotSectorsStatus;
  dataMode?: HotSectorsDataMode;
  message?: string;
  provider?: string | null;
  asOf?: string | null;
  isRealtime?: boolean;
  isDelayed?: boolean;
  delayMinutes?: number | null;
  flowDefinition?: HotSectorFlowDefinition | null;
  isLoading?: boolean;
  className?: string;
}

function getStatusBadgeLabel(
  status: HotSectorsStatus,
  dataMode: HotSectorsDataMode,
  labels: {
    live: string;
    delayed: string;
    mock: string;
    demo: string;
    unavailable: string;
  },
): string {
  if (status === "unavailable" || dataMode === "none") {
    return labels.unavailable;
  }
  if (dataMode === "mock") {
    return labels.mock;
  }
  if (dataMode === "demo") {
    return labels.demo;
  }
  if (dataMode === "delayed") {
    return labels.delayed;
  }
  return labels.live;
}

function getEmptyMessage(
  status: HotSectorsStatus,
  dataMode: HotSectorsDataMode,
  labels: {
    emptyLive: string;
    emptyDelayed: string;
    emptyDemo: string;
    emptyMock: string;
    unavailable: string;
  },
): string {
  if (status === "unavailable" || dataMode === "none") {
    return labels.unavailable;
  }
  if (dataMode === "mock") {
    return labels.emptyMock;
  }
  if (dataMode === "demo") {
    return labels.emptyDemo;
  }
  if (dataMode === "delayed") {
    return labels.emptyDelayed;
  }
  return labels.emptyLive;
}

export function HotSectors({
  sectors,
  status = "ok",
  dataMode = "live",
  message,
  provider = null,
  asOf = null,
  isRealtime = false,
  isDelayed = false,
  delayMinutes = null,
  flowDefinition = null,
  isLoading = false,
  className = "",
}: HotSectorsProps) {
  const t = useTranslations("Dashboard");
  const { getMovementColor } = useMarketColorsContext();
  const statusBadgeLabel = getStatusBadgeLabel(status, dataMode, {
    live: t("hotSectorsLiveBadge"),
    delayed: t("hotSectorsDelayedBadge"),
    mock: t("hotSectorsMockBadge"),
    demo: t("hotSectorsDemoBadge"),
    unavailable: t("hotSectorsUnavailableBadge"),
  });
  const statusBadgeVariant = status === "ok" && dataMode === "live" ? "outline" : "secondary";
  const shouldShowDataCaution = status !== "ok" || dataMode === "mock" || dataMode === "demo" || dataMode === "none";

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-base">🔥 {t("hotSectorsTitle")}</CardTitle>
          <CardDescription className="text-xs">{t("hotSectorsDesc")}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (sectors.length === 0) {
    const emptyMessage = getEmptyMessage(status, dataMode, {
      emptyLive: t("hotSectorsEmptyLive"),
      emptyDelayed: t("hotSectorsEmptyDelayed"),
      emptyDemo: t("hotSectorsEmptyDemo"),
      emptyMock: t("hotSectorsEmptyMock"),
      unavailable: t("hotSectorsUnavailable"),
    });

    return (
      <Card className={className}>
        <CardHeader>
          <div className="flex items-center justify-between gap-2">
            <CardTitle className="text-base">🔥 {t("hotSectorsTitle")}</CardTitle>
            <Badge variant={statusBadgeVariant}>{statusBadgeLabel}</Badge>
          </div>
          <CardDescription className="text-xs">{message ?? t("hotSectorsDesc")}</CardDescription>
          <HotSectorMetadata
            provider={provider}
            asOf={asOf}
            isRealtime={isRealtime}
            isDelayed={isDelayed}
            delayMinutes={delayMinutes}
            flowDefinition={flowDefinition}
          />
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-sm text-muted-foreground">
            {emptyMessage}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-base">🔥 {t("hotSectorsTitle")}</CardTitle>
          <Badge variant={statusBadgeVariant}>{statusBadgeLabel}</Badge>
        </div>
        <CardDescription className="text-xs">
          {message ?? t("hotSectorsDesc")} · Top {sectors.length}
        </CardDescription>
        <HotSectorMetadata
          provider={provider}
          asOf={asOf}
          isRealtime={isRealtime}
          isDelayed={isDelayed}
          delayMinutes={delayMinutes}
          flowDefinition={flowDefinition}
        />
      </CardHeader>
      <CardContent className="space-y-3">
        {shouldShowDataCaution ? (
          <div className="rounded-md border bg-muted/30 p-3 text-xs text-muted-foreground">
            {t("hotSectorsDataCaution")}
          </div>
        ) : null}
        {sectors.map((sector, index) => {
          const sectorChangePercent = safeNumber(sector.change_percent);
          const leaderChangePercent = safeNumber(sector.leader_change_percent ?? sector.leader?.change_percent);
          const isPositive = sectorChangePercent !== null && sectorChangePercent > 0;
          const isNegative = sectorChangePercent !== null && sectorChangePercent < 0;
          const flowDirection = resolveFlowDirection(sector);
          const isFlowIn = flowDirection === "inflow";
          const isFlowOut = flowDirection === "outflow";
          const leaderName = sector.leader_name ?? sector.leader?.name ?? t("unavailableShort");
          const flowLabel = getFlowDirectionLabel(flowDirection, {
            inflow: t("hotSectorsFlowIn"),
            outflow: t("hotSectorsFlowOut"),
            flat: t("hotSectorsFlowFlat"),
            unknown: t("hotSectorsFlowUnknown"),
          });
          const topConstituentNames = (sector.top_constituents ?? [])
            .map((constituent) => constituent.name || constituent.symbol)
            .filter(Boolean)
            .slice(0, 3)
            .join(" / ");
          const breadthSummary = getBreadthSummary(sector.breadth, {
            unavailable: t("hotSectorsBreadthUnavailable"),
          });
          const positiveContributionSummary = getContributionSummary(sector.constituent_contribution?.top_positive);
          const negativeContributionSummary = getContributionSummary(sector.constituent_contribution?.top_negative);
          const historySummary = getHistorySummary(sector.history, {
            unavailable: t("hotSectorsHistoryUnavailable"),
          });

          return (
            <div
              key={sector.sector_id ?? `${sector.name}-${index}`}
              className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/30 transition-colors"
            >
              <div className="flex items-center gap-3 flex-1">
                <div className="text-lg font-bold text-muted-foreground w-6">
                  {index + 1}
                </div>
                
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="font-semibold text-sm">{sector.name}</h4>
                    <Badge variant="outline" className="text-xs">
                      {sector.symbols_count}只
                    </Badge>
                    {sector.is_verified ? (
                      <Badge variant="outline" className="text-xs">
                        {t("hotSectorsVerified")}
                      </Badge>
                    ) : null}
                  </div>
                  
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span>{t("hotSectorsLeader", { name: leaderName })}</span>
                    <span className={getMovementColor(leaderChangePercent ?? 0)}>
                      {formatSignedPercent(leaderChangePercent)}
                    </span>
                  </div>
                  {topConstituentNames ? (
                    <div className="mt-1 text-xs text-muted-foreground">
                      {t("hotSectorsTopConstituents", { names: topConstituentNames })}
                    </div>
                  ) : null}
                  {sector.flow_definition ? (
                    <div className="mt-1 text-xs text-muted-foreground">
                      {t("hotSectorsFlowDefinition", { definition: sector.flow_definition })}
                    </div>
                  ) : null}
                  {breadthSummary ? (
                    <div className="mt-1 text-xs text-muted-foreground">
                      {t("hotSectorsBreadth", { summary: breadthSummary })}
                    </div>
                  ) : null}
                  {positiveContributionSummary ? (
                    <div className="mt-1 text-xs text-muted-foreground">
                      {t("hotSectorsContributionPositive", { names: positiveContributionSummary })}
                    </div>
                  ) : null}
                  {negativeContributionSummary ? (
                    <div className="mt-1 text-xs text-muted-foreground">
                      {t("hotSectorsContributionNegative", { names: negativeContributionSummary })}
                    </div>
                  ) : null}
                  {sector.taxonomy?.taxonomy_version ? (
                    <div className="mt-1 text-xs text-muted-foreground">
                      {t("hotSectorsTaxonomy", { version: sector.taxonomy.taxonomy_version })}
                    </div>
                  ) : null}
                  {historySummary ? (
                    <div className="mt-1 text-xs text-muted-foreground">
                      {t("hotSectorsRotationHistory", { summary: historySummary })}
                    </div>
                  ) : null}
                </div>
              </div>

              <div className="flex flex-col items-end gap-1">
                <div className={`flex items-center gap-1 font-semibold ${getMovementColor(sectorChangePercent ?? 0)}`}>
                  {isPositive ? (
                    <TrendingUp className="h-4 w-4" />
                  ) : isNegative ? (
                    <TrendingDown className="h-4 w-4" />
                  ) : null}
                  <span>{formatSignedPercent(sectorChangePercent)}</span>
                </div>
                
                <div className={`flex items-center gap-1 text-xs ${isFlowIn ? getMovementColor(1) : isFlowOut ? getMovementColor(-1) : "text-muted-foreground"}`}>
                  {isFlowIn ? (
                    <ArrowUpRight className="h-3 w-3" />
                  ) : isFlowOut ? (
                    <ArrowDownRight className="h-3 w-3" />
                  ) : null}
                  <span>{flowLabel} {formatFlowAmount(sector, t("unavailableShort"))}</span>
                </div>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

function HotSectorMetadata({
  provider,
  asOf,
  isRealtime,
  isDelayed,
  delayMinutes,
  flowDefinition,
}: {
  provider?: string | null;
  asOf?: string | null;
  isRealtime?: boolean;
  isDelayed?: boolean;
  delayMinutes?: number | null;
  flowDefinition?: HotSectorFlowDefinition | null;
}) {
  const t = useTranslations("Dashboard");
  const metadataItems = [
    provider ? t("hotSectorsProvider", { provider }) : null,
    asOf ? t("hotSectorsAsOf", { date: asOf }) : null,
    isRealtime ? t("hotSectorsRealtime") : null,
    isDelayed && delayMinutes !== null && delayMinutes !== undefined
      ? t("hotSectorsDelayedByMinutes", { minutes: delayMinutes })
      : null,
    flowDefinition?.methodology
      ? t("hotSectorsFlowDefinition", { definition: flowDefinition.methodology })
      : null,
  ].filter(Boolean);

  if (metadataItems.length === 0) {
    return null;
  }

  return <div className="text-xs text-muted-foreground">{metadataItems.join(" · ")}</div>;
}

function resolveFlowDirection(sector: Sector): FlowDirection {
  const normalizedDirection = sector.flow_direction?.trim().toLowerCase();
  if (
    normalizedDirection === "inflow" ||
    normalizedDirection === "outflow" ||
    normalizedDirection === "flat" ||
    normalizedDirection === "unknown"
  ) {
    return normalizedDirection;
  }
  if (sector.fund_flow === "流入") {
    return "inflow";
  }
  if (sector.fund_flow === "流出") {
    return "outflow";
  }
  const netFlowAmount = safeNumber(sector.net_flow_amount ?? sector.fund_flow_amount);
  if (netFlowAmount === null) {
    return "unknown";
  }
  if (netFlowAmount > 0) {
    return "inflow";
  }
  if (netFlowAmount < 0) {
    return "outflow";
  }
  return "flat";
}

function getFlowDirectionLabel(
  flowDirection: FlowDirection,
  labels: Record<FlowDirection, string>,
): string {
  return labels[flowDirection];
}

function safeNumber(value: number | null | undefined): number | null {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return null;
  }
  return value;
}

function formatSignedPercent(value: number | null): string {
  if (value === null) {
    return "--";
  }
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

function formatFlowAmount(sector: Sector, unavailableLabel: string): string {
  const displayAmount = safeNumber(sector.fund_flow_amount);
  if (displayAmount !== null) {
    return `${Math.abs(displayAmount).toLocaleString(undefined, { maximumFractionDigits: 1 })}亿`;
  }
  const netFlowAmount = safeNumber(sector.net_flow_amount);
  if (netFlowAmount === null) {
    return unavailableLabel;
  }
  const currency = sector.net_flow_currency ?? "";
  return `${Math.abs(netFlowAmount).toLocaleString()}${currency ? ` ${currency}` : ""}`;
}

function getBreadthSummary(
  breadth: HotSectorBreadth | null | undefined,
  labels: { unavailable: string },
): string | null {
  if (!breadth) {
    return null;
  }
  const advancers = safeNumber(breadth.advancers);
  const decliners = safeNumber(breadth.decliners);
  const unchanged = safeNumber(breadth.unchanged);
  const total = safeNumber(breadth.total);
  if (advancers === null || decliners === null || unchanged === null || total === null) {
    return breadth.status === "unavailable" ? labels.unavailable : null;
  }
  const ratio = safeNumber(breadth.advance_decline_ratio);
  const ratioText = ratio === null ? "--" : ratio.toFixed(2);
  return `${advancers}/${decliners}/${unchanged} · ${total} · A/D ${ratioText}`;
}

function getContributionSummary(entries: HotSectorContributionEntry[] | null | undefined): string | null {
  const names = (entries ?? [])
    .map((entry) => entry.name || entry.symbol)
    .filter(Boolean)
    .slice(0, 3)
    .join(" / ");
  return names || null;
}

function getHistorySummary(
  history: HotSectorHistory | null | undefined,
  labels: { unavailable: string },
): string | null {
  if (!history) {
    return null;
  }
  if (history.status === "unavailable") {
    return labels.unavailable;
  }
  const snapshotCount = safeNumber(history.snapshot_count);
  if (snapshotCount === null) {
    return null;
  }
  return `${snapshotCount}`;
}
