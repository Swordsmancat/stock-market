"use client";

import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";

type AnalysisRefreshPayload = {
  symbol: string;
  status: string;
  report: { report_type: string };
};

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
        provider: process.env.NEXT_PUBLIC_MARKET_DATA_PROVIDER ?? "mock",
      });
      const response = await fetch(`/api/analysis/refresh?${params.toString()}`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error("Analysis refresh request failed");
      }
      const payload = (await response.json()) as AnalysisRefreshPayload;
      setMessage(`✅ ${payload.symbol} refreshed`);
    } catch {
      setMessage("❌ Failed");
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
