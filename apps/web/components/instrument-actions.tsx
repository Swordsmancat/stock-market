"use client";

import { ExternalLink } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link } from "@/src/i18n/routing";

import { Button } from "@/components/ui/button";
import { AnalysisRefreshButton } from "@/app/[locale]/AnalysisRefreshButton";
import { GenerateDailyReportButton } from "@/components/generate-daily-report-button";

type InstrumentQuickActionsProps = {
  symbol: string;
  market: string;
  analysisStart: string;
  analysisEnd: string;
  provider: string;
  watchlistForm: React.ReactNode;
};

export function InstrumentQuickActions({
  symbol,
  market,
  analysisStart,
  analysisEnd,
  provider,
  watchlistForm,
}: InstrumentQuickActionsProps) {
  const t = useTranslations("InstrumentDetail");

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-start">
      {watchlistForm}
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
        provider={provider}
      />
    </div>
  );
}
