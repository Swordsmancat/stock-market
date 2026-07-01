import { ExternalLink } from "lucide-react";
import { getTranslations } from "next-intl/server";
import { Link } from "@/src/i18n/routing";

import { Button } from "@/components/ui/button";
import {
  InstrumentAnalysisRefreshForm,
  InstrumentGenerateReportForm,
} from "@/components/instrument-analysis-forms";

type InstrumentQuickActionsProps = {
  locale: string;
  symbol: string;
  market: string;
  analysisStart: string;
  analysisEnd: string;
  provider: string;
  watchlistForm: React.ReactNode;
};

export async function InstrumentQuickActions({
  locale,
  symbol,
  market,
  analysisStart,
  analysisEnd,
  provider,
  watchlistForm,
}: InstrumentQuickActionsProps) {
  const t = await getTranslations("InstrumentDetail");
  const returnTo = `/${locale}/instruments/${encodeURIComponent(symbol)}`;

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-start">
      {watchlistForm}
      <Button variant="outline" size="sm" asChild>
        <Link href={`/reports?symbol=${symbol}` as any}>
          <ExternalLink className="mr-2 h-4 w-4" />
          {t("viewReports")}
        </Link>
      </Button>
      <InstrumentGenerateReportForm
        locale={locale}
        symbol={symbol}
        start={analysisStart}
        end={analysisEnd}
        returnTo={returnTo}
        label={t("generateReport")}
      />
      <InstrumentAnalysisRefreshForm
        locale={locale}
        symbol={symbol}
        market={market}
        start={analysisStart}
        end={analysisEnd}
        maWindow={3}
        provider={provider}
        returnTo={returnTo}
        label={t("refreshAnalysis")}
      />
    </div>
  );
}
