"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Database } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { ActionFeedback } from "@/components/action-feedback";
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
  const router = useRouter();
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
      const taskRun = await enqueueAndPoll(
        `/api/ingestion/mock-snapshot?${params.toString()}`,
        { taskName: "ingestion.ingest_market_data" },
      );
      const result = taskRun.result_json as { market?: string; bar_count?: number } | null;
      const barCount = result?.bar_count ?? 0;
      if (barCount === 0) {
        setMessage(`❌ ${t("ingestionEmpty")}`);
        return;
      }
      setMessage(`✅ ${result?.market ?? market}: ${barCount} bars`);
      router.refresh();
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Request failed";
      setMessage(`❌ ${detail}`);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex w-full max-w-md flex-col gap-2">
      <Button type="button" onClick={handleClick} disabled={isLoading} variant="outline" className="w-fit">
        <Database className={`mr-2 h-4 w-4 ${isLoading ? "animate-pulse" : ""}`} />
        {isLoading ? t("ingesting") : t("triggerIngestion")}
      </Button>
      <ActionFeedback message={message} />
    </div>
  );
}
