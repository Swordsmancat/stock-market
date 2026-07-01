import { triggerIngestionAction } from "@/app/[locale]/actions";
import { Button } from "@/components/ui/button";

type IngestionTriggerFormProps = {
  locale: string;
  market: string;
  start: string;
  end: string;
  provider: string;
  label: string;
};

export function IngestionTriggerForm({
  locale,
  market,
  start,
  end,
  provider,
  label,
}: IngestionTriggerFormProps) {
  return (
    <form action={triggerIngestionAction} className="inline-block">
      <input type="hidden" name="locale" value={locale} />
      <input type="hidden" name="market" value={market} />
      <input type="hidden" name="start" value={start} />
      <input type="hidden" name="end" value={end} />
      <input type="hidden" name="provider" value={provider} />
      <Button type="submit" variant="outline">
        {label}
      </Button>
    </form>
  );
}
