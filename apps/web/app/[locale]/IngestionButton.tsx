"use client";

import { useState } from "react";
import { Database } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";

type IngestionPayload = {
  status: string;
  market: string;
  bar_count: number;
};

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
        provider: process.env.NEXT_PUBLIC_MARKET_DATA_PROVIDER ?? "mock",
      });
      const response = await fetch(`/api/ingestion/mock-snapshot?${params.toString()}`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error("Ingestion request failed");
      }
      const payload = (await response.json()) as IngestionPayload;
      setMessage(`✅ ${payload.market}: ${payload.bar_count} bars`);
    } catch {
      setMessage("❌ Failed");
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
