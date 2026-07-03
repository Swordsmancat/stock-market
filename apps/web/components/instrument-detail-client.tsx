"use client";

import { useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AdvancedCandlestickChart } from "@/components/advanced-candlestick-chart";
import { IntradayPriceChart } from "@/components/intraday-price-chart";
import { MarketDepthCard } from "@/components/market-depth-card";
import { PriceChangeBadge } from "@/components/price-change-badge";
import { decodeInstrumentSymbol, getInstrumentDisplayName } from "@/lib/instrument-display";
import type { InstrumentDetailPayload } from "@/lib/instrument-detail";

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
  const latestBar = bars.at(-1) ?? data.latest?.item ?? null;
  const prevBar = bars.at(-2) ?? null;
  
  const currentPrice = latestBar?.close || 0;
  const prevPrice = prevBar?.close || currentPrice;
  const change = currentPrice - prevPrice;
  const changePercent = prevPrice ? change / prevPrice : 0;
  const decodedSymbol = decodeInstrumentSymbol(symbol);
  const displayName = getInstrumentDisplayName(symbol, locale);
  const subtitle = displayName === decodedSymbol ? t("detailSubtitle") : `${decodedSymbol} · ${t("detailSubtitle")}`;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          {t("back")}
        </Button>
      </div>

      <div>
        <h1 className="text-3xl font-bold">{displayName}</h1>
        <p className="text-muted-foreground">{subtitle}</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>{t("latestPriceCard")}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{currentPrice.toFixed(2)}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardDescription>{t("priceChange")}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {change >= 0 ? '+' : ''}{change.toFixed(2)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardDescription>{t("priceChangePercent")}</CardDescription>
          </CardHeader>
          <CardContent>
            <PriceChangeBadge
              percentChange={changePercent}
              absoluteChange={change}
              marketType="CN"
              showArrow
              className="text-lg"
            />
          </CardContent>
        </Card>
      </div>

      <MarketDepthCard marketDepth={data.market_depth ?? null} />

      <Card>
        <CardHeader>
          <CardTitle>{t("intradayTitle")}</CardTitle>
          <CardDescription>{t("intradayDescription")}</CardDescription>
        </CardHeader>
        <CardContent>
          <IntradayPriceChart
            points={data.intraday?.items ?? []}
            previousClose={data.intraday?.previous_close ?? null}
            status={data.intraday?.status ?? "degraded"}
            reason={data.intraday?.availability?.reason ?? null}
            height={280}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("klineTitle")}</CardTitle>
          <CardDescription>{t("interactiveKlineDescription")}</CardDescription>
        </CardHeader>
        <CardContent>
          {bars.length > 0 ? (
            <AdvancedCandlestickChart
              data={bars}
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
