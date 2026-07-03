"use client";

import { TrendingUp, TrendingDown, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { useTranslations } from "next-intl";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

type HotSectorsStatus = "ok" | "degraded" | "unavailable";
type HotSectorsDataMode = "live" | "demo" | "mock" | "none";

interface Sector {
  name: string;
  name_en: string;
  change_percent: number;
  fund_flow: string;
  fund_flow_amount: number;
  leader_symbol: string;
  leader_name: string;
  leader_change_percent: number;
  symbols_count: number;
}

interface HotSectorsProps {
  sectors: Sector[];
  status?: HotSectorsStatus;
  dataMode?: HotSectorsDataMode;
  message?: string;
  isLoading?: boolean;
  className?: string;
}

function getStatusBadgeLabel(
  status: HotSectorsStatus,
  dataMode: HotSectorsDataMode,
  labels: {
    live: string;
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
  return labels.live;
}

function getEmptyMessage(
  status: HotSectorsStatus,
  dataMode: HotSectorsDataMode,
  labels: {
    emptyLive: string;
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
  return labels.emptyLive;
}

export function HotSectors({
  sectors,
  status = "ok",
  dataMode = "live",
  message,
  isLoading = false,
  className = "",
}: HotSectorsProps) {
  const t = useTranslations("Dashboard");
  const statusBadgeLabel = getStatusBadgeLabel(status, dataMode, {
    live: t("hotSectorsLiveBadge"),
    mock: t("hotSectorsMockBadge"),
    demo: t("hotSectorsDemoBadge"),
    unavailable: t("hotSectorsUnavailableBadge"),
  });
  const statusBadgeVariant = status === "ok" && dataMode === "live" ? "outline" : "secondary";

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
      </CardHeader>
      <CardContent className="space-y-3">
        {sectors.map((sector, index) => {
          const isPositive = sector.change_percent >= 0;
          const isFlowIn = sector.fund_flow === "流入";

          return (
            <div
              key={index}
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
                  </div>
                  
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span>龙头: {sector.leader_name}</span>
                    <span className={isPositive ? "text-green-600" : "text-red-600"}>
                      {isPositive ? "+" : ""}{sector.leader_change_percent.toFixed(2)}%
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex flex-col items-end gap-1">
                <div className={`flex items-center gap-1 font-semibold ${isPositive ? "text-green-600" : "text-red-600"}`}>
                  {isPositive ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                  <span>{isPositive ? "+" : ""}{sector.change_percent.toFixed(2)}%</span>
                </div>
                
                <div className={`flex items-center gap-1 text-xs ${isFlowIn ? "text-green-600" : "text-red-600"}`}>
                  {isFlowIn ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                  <span>{sector.fund_flow} {Math.abs(sector.fund_flow_amount).toFixed(1)}亿</span>
                </div>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
