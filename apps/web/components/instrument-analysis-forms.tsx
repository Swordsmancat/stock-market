import { refreshAnalysisAction, generateDailyReportAction } from "@/app/[locale]/actions";
import { Button } from "@/components/ui/button";

type InstrumentAnalysisRefreshFormProps = {
  locale: string;
  symbol: string;
  market: string;
  start: string;
  end: string;
  maWindow: number;
  provider: string;
  returnTo: string;
  label: string;
};

export function InstrumentAnalysisRefreshForm({
  locale,
  symbol,
  market,
  start,
  end,
  maWindow,
  provider,
  returnTo,
  label,
}: InstrumentAnalysisRefreshFormProps) {
  return (
    <form action={refreshAnalysisAction} className="inline-block">
      <input type="hidden" name="locale" value={locale} />
      <input type="hidden" name="symbol" value={symbol} />
      <input type="hidden" name="market" value={market} />
      <input type="hidden" name="start" value={start} />
      <input type="hidden" name="end" value={end} />
      <input type="hidden" name="ma_window" value={String(maWindow)} />
      <input type="hidden" name="provider" value={provider} />
      <input type="hidden" name="return_to" value={returnTo} />
      <Button type="submit" variant="outline" size="sm">
        {label}
      </Button>
    </form>
  );
}

type InstrumentGenerateReportFormProps = {
  locale: string;
  symbol: string;
  start: string;
  end: string;
  returnTo: string;
  label: string;
};

export function InstrumentGenerateReportForm({
  locale,
  symbol,
  start,
  end,
  returnTo,
  label,
}: InstrumentGenerateReportFormProps) {
  return (
    <form action={generateDailyReportAction} className="inline-block">
      <input type="hidden" name="locale" value={locale} />
      <input type="hidden" name="symbol" value={symbol} />
      <input type="hidden" name="start" value={start} />
      <input type="hidden" name="end" value={end} />
      <input type="hidden" name="return_to" value={returnTo} />
      <Button type="submit" variant="outline" size="sm">
        {label}
      </Button>
    </form>
  );
}
