"use client";

import { useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AdvancedCandlestickChart } from "@/components/advanced-candlestick-chart";
import { IntradayPriceChart } from "@/components/intraday-price-chart";
import { MarketAssistantCard } from "@/components/market-assistant-card";
import { MarketDepthCard } from "@/components/market-depth-card";
import { DataTrustBadge } from "@/components/data-trust-badge";
import { FinancialPageHeader } from "@/components/financial-page-header";
import { useMarketColorsContext } from "@/context/market-colors-context";
import { createDataTrustSignal } from "@/lib/data-trust";
import { decodeInstrumentSymbol, getInstrumentDisplayName } from "@/lib/instrument-display";
import type { InstrumentBar, InstrumentDetailPayload } from "@/lib/instrument-detail";

type ChartBarData = InstrumentBar & {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
};

function isChartBarData(bar: InstrumentBar): bar is ChartBarData {
  return (
    typeof bar.timestamp === "string" &&
    Number.isFinite(bar.open) &&
    Number.isFinite(bar.high) &&
    Number.isFinite(bar.low) &&
    Number.isFinite(bar.close)
  );
}

interface InstrumentDetailClientProps {
  symbol: string;
  locale: string;
  initialData?: InstrumentDetailPayload | null;
  initialError?: string | null;
}

export function InstrumentDetailClient({
  symbol,
  locale,
  initialData = null,
  initialError = null,
}: InstrumentDetailClientProps) {
  const router = useRouter();
  const t = useTranslations("InstrumentDetail");
  const { getMovementColor } = useMarketColorsContext();
  const [data, setData] = useState<InstrumentDetailPayload | null>(initialData);
  const [loading, setLoading] = useState(initialData === null && initialError === null);
  const [error, setError] = useState<string | null>(initialError);

  useEffect(() => {
    if (initialData !== null || initialError !== null) {
      return;
    }

    async function fetchData() {
      try {
        setLoading(true);
        const response = await fetch(`/api/instruments/${encodeURIComponent(symbol)}`);
        
        if (!response.ok) {
          throw new Error("Failed to fetch instrument data");
        }

        const result = await response.json();
        setData(result);
      } catch (err) {
        console.error("Fetch error:", err);
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [symbol]);

  if (loading) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          {t("back")}
        </Button>
        <div className="flex items-center justify-center h-96">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          {t("back")}
        </Button>
        <Card>
          <CardContent className="p-6">
            <p className="text-center text-destructive">
              {t("loadFailed", { reason: error ?? t("unavailableShort") })}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const bars = data.bars?.items ?? [];
  const chartBars = bars.filter(isChartBarData);
  const latestBar = bars.at(-1) ?? data.latest?.item ?? null;
  const prevBar = bars.at(-2) ?? null;
  
  const currentPrice = latestBar?.close || 0;
  const prevPrice = prevBar?.close || currentPrice;
  const change = currentPrice - prevPrice;
  const changePercent = prevPrice ? change / prevPrice : 0;
  const formattedChange = `${change >= 0 ? "+" : ""}${change.toFixed(2)}`;
  const formattedChangePercent = `${changePercent >= 0 ? "+" : ""}${(changePercent * 100).toFixed(2)}%`;
  const decodedSymbol = decodeInstrumentSymbol(symbol);
  const displayName = getInstrumentDisplayName(symbol, locale);
  const subtitle = displayName === decodedSymbol ? t("detailSubtitle") : `${decodedSymbol} · ${t("detailSubtitle")}`;
  const assistantSymbol = data.request_symbol ?? symbol;
  const assistantProvider = data.market_depth?.effective_provider ?? data.market_depth?.provider ?? null;
  const latestTrustSignal = createDataTrustSignal({
    status: data.latest?.status,
    source: data.latest?.source,
    provider: data.latest?.provider,
    requested_provider: data.latest?.requested_provider,
    effective_provider: data.latest?.effective_provider,
    as_of: data.latest?.item?.timestamp,
    no_data_reason: data.latest?.no_data_reason,
  });
  const barsTrustSignal = createDataTrustSignal({
    status: data.bars?.status,
    source: data.bars?.source,
    provider: data.bars?.provider,
    requested_provider: data.bars?.requested_provider,
    effective_provider: data.bars?.effective_provider,
    as_of: latestBar?.timestamp,
    no_data_reason: data.bars?.no_data_reason,
  });

  return (
    <div className="space-y-6">
      <FinancialPageHeader
        title={displayName}
        description={subtitle}
        badges={[
          { label: decodedSymbol, variant: "secondary" },
          { label: `provider: ${assistantProvider ?? data.latest?.effective_provider ?? data.latest?.provider ?? "none"}` },
          { label: `${data.range?.start ?? "-"} / ${data.range?.end ?? "-"}` },
        ]}
        metrics={[
          {
            label: t("latestPriceCard"),
            value: currentPrice.toFixed(2),
            description: <DataTrustBadge signal={latestTrustSignal} mode="summary" />,
          },
          {
            label: t("priceChange"),
            value: formattedChange,
            className: getMovementColor(change),
          },
          {
            label: t("priceChangePercent"),
            value: formattedChangePercent,
            className: getMovementColor(change),
          },
          {
            label: t("klineTitle"),
            value: chartBars.length,
            description: <DataTrustBadge signal={barsTrustSignal} mode="summary" />,
          },
        ]}
        actions={
          <Button variant="outline" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4" />
            {t("back")}
          </Button>
        }
      />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(22rem,0.85fr)]">
        <MarketAssistantCard
          symbol={assistantSymbol}
          locale={locale}
          provider={assistantProvider}
          start={data.range?.start ?? null}
          end={data.range?.end ?? null}
        />

        <MarketDepthCard marketDepth={data.market_depth ?? null} />
      </div>

      <Card className="rounded-md shadow-none">
        <CardHeader className="border-b bg-muted/20 p-4">
          <CardTitle>{t("intradayTitle")}</CardTitle>
          <CardDescription>{t("intradayDescription")}</CardDescription>
        </CardHeader>
        <CardContent className="p-4">
          <IntradayPriceChart
            points={data.intraday?.items ?? []}
            previousClose={data.intraday?.previous_close ?? null}
            status={data.intraday?.status ?? "degraded"}
            reason={data.intraday?.availability?.reason ?? null}
            source={data.intraday?.source ?? null}
            provider={data.intraday?.provider ?? null}
            requestedProvider={data.intraday?.requested_provider ?? null}
            effectiveProvider={data.intraday?.effective_provider ?? null}
            availability={data.intraday?.availability ?? null}
            freshness={data.intraday?.freshness ?? null}
            session={data.intraday?.session ?? null}
            height={280}
          />
        </CardContent>
      </Card>

      <Card className="rounded-md shadow-none">
        <CardHeader className="border-b bg-muted/20 p-4">
          <CardTitle>{t("klineTitle")}</CardTitle>
          <CardDescription>{t("interactiveKlineDescription")}</CardDescription>
        </CardHeader>
        <CardContent className="p-4">
          <div className="mb-4">
            <DataTrustBadge signal={barsTrustSignal} mode="summary" />
          </div>
          {chartBars.length > 0 ? (
            <AdvancedCandlestickChart
              data={chartBars}
              symbol={symbol}
              height={500}
              showMA={true}
              showVolume={true}
            />
          ) : (
            <div className="flex items-center justify-center h-96 text-muted-foreground">
              {t("noKlineData")}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
