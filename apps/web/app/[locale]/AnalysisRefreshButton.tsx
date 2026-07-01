"use client";

import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { getMarketDataProvider } from "@/lib/market-data";
import { enqueueAndPoll } from "@/lib/task-run-poll";

type AnalysisRefreshButtonProps = {
  symbol: string;
  market: string;
  start: string;
  end: string;
  maWindow: number;
};

export function AnalysisRefreshButton({
  symbol,
  market,
  start,
  end,
  maWindow,
}: AnalysisRefreshButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const t = useTranslations("Dashboard");

  async function handleClick() {
    setIsLoading(true);
    setMessage(null);

    try {
      const params = new URLSearchParams({
        symbol,
        market,
        start,
        end,
        ma_window: String(maWindow),
        provider: getMarketDataProvider(),
      });
      const taskRun = await enqueueAndPoll(`/api/analysis/refresh?${params.toString()}`);
      const result = taskRun.result_json as { symbol?: string } | null;
      setMessage(`✅ ${result?.symbol ?? symbol} refreshed`);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Request failed";
      setMessage(`❌ ${detail}`);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <Button onClick={handleClick} disabled={isLoading} className="w-fit">
        <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
        {isLoading ? t("refreshing") : t("refreshAnalysis")}
      </Button>
      {message ? <p className="text-sm text-muted-foreground">{message}</p> : null}
    </div>
  );
}
