"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Plus, ExternalLink } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link } from "@/src/i18n/routing";

import { Button } from "@/components/ui/button";
import { AnalysisRefreshButton } from "@/app/[locale]/AnalysisRefreshButton";
import { GenerateDailyReportButton } from "@/components/generate-daily-report-button";

type InstrumentQuickActionsProps = {
  symbol: string;
  market: string;
  name?: string;
  analysisStart: string;
  analysisEnd: string;
};

export function InstrumentQuickActions({
  symbol,
  market,
  name,
  analysisStart,
  analysisEnd,
}: InstrumentQuickActionsProps) {
  const [isPending, startTransition] = React.useTransition();
  const [message, setMessage] = React.useState<string | null>(null);
  const router = useRouter();
  const t = useTranslations("InstrumentDetail");

  function handleAddToWatchlist() {
    startTransition(async () => {
      setMessage(null);
      const response = await fetch("/api/watchlist/items", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          symbol,
          market,
          name: name ?? null,
          alert_rules: {},
        }),
      });
      if (!response.ok) {
        setMessage(t("watchlistFailed"));
        return;
      }
      setMessage(t("watchlistAdded"));
      router.refresh();
    });
  }

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-start">
      <Button variant="outline" size="sm" disabled={isPending} onClick={handleAddToWatchlist}>
        <Plus className="mr-2 h-4 w-4" />
        {isPending ? t("addingToWatchlist") : t("addToWatchlist")}
      </Button>
      <Button variant="outline" size="sm" asChild>
        <Link href={`/reports?symbol=${symbol}` as any}>
          <ExternalLink className="mr-2 h-4 w-4" />
          {t("viewReports")}
        </Link>
      </Button>
      <GenerateDailyReportButton symbol={symbol} start={analysisStart} end={analysisEnd} />
      <AnalysisRefreshButton
        symbol={symbol}
        market={market}
        start={analysisStart}
        end={analysisEnd}
        maWindow={3}
      />
      {message ? <p className="w-full text-sm text-muted-foreground">{message}</p> : null}
    </div>
  );
}
