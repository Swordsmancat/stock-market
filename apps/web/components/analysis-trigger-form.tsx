import { refreshAnalysisAction } from "@/app/[locale]/actions";
import { Button } from "@/components/ui/button";

type AnalysisTriggerFormProps = {
  locale: string;
  symbol: string;
  market: string;
  start: string;
  end: string;
  maWindow: number;
  provider: string;
  label: string;
};

export function AnalysisTriggerForm({
  locale,
  symbol,
  market,
  start,
  end,
  maWindow,
  provider,
  label,
}: AnalysisTriggerFormProps) {
  return (
    <form action={refreshAnalysisAction} className="inline-block">
      <input type="hidden" name="locale" value={locale} />
      <input type="hidden" name="symbol" value={symbol} />
      <input type="hidden" name="market" value={market} />
      <input type="hidden" name="start" value={start} />
      <input type="hidden" name="end" value={end} />
      <input type="hidden" name="ma_window" value={String(maWindow)} />
      <input type="hidden" name="provider" value={provider} />
      <Button type="submit">{label}</Button>
    </form>
  );
}
