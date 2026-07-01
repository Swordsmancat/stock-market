"use client";

import { useState } from "react";
import { Database } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { getMarketDataProvider } from "@/lib/market-data";
import { enqueueAndPoll } from "@/lib/task-run-poll";

type IngestionButtonProps = {
  market: string;
  start: string;
  end: string;
};

export function IngestionButton({ market, start, end }: IngestionButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const t = useTranslations("Dashboard");

  async function handleClick() {
    setIsLoading(true);
    setMessage(null);

    try {
      const params = new URLSearchParams({
        market,
        start,
        end,
        provider: getMarketDataProvider(),
      });
      const taskRun = await enqueueAndPoll(`/api/ingestion/mock-snapshot?${params.toString()}`);
      const result = taskRun.result_json as { market?: string; bar_count?: number } | null;
      const barCount = result?.bar_count ?? 0;
      if (barCount === 0) {
        setMessage(t("ingestionEmpty"));
        return;
      }
      setMessage(`✅ ${result?.market ?? market}: ${barCount} bars`);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Request failed";
      setMessage(`❌ ${detail}`);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <Button onClick={handleClick} disabled={isLoading} variant="outline" className="w-fit">
        <Database className="mr-2 h-4 w-4" />
        {isLoading ? t("ingesting") : t("triggerIngestion")}
      </Button>
      {message ? <p className="text-sm text-muted-foreground">{message}</p> : null}
    </div>
  );
}
