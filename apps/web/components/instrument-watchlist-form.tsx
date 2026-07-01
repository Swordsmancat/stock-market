import { getTranslations } from "next-intl/server";
import { Plus } from "lucide-react";

import { addInstrumentToWatchlistAction } from "@/app/[locale]/actions";
import { Button } from "@/components/ui/button";

type InstrumentWatchlistFormProps = {
  locale: string;
  symbol: string;
  market: string;
  name?: string;
};

export async function InstrumentWatchlistForm({
  locale,
  symbol,
  market,
  name = "",
}: InstrumentWatchlistFormProps) {
  const t = await getTranslations("InstrumentDetail");

  return (
    <form action={addInstrumentToWatchlistAction}>
      <input type="hidden" name="locale" value={locale} />
      <input type="hidden" name="symbol" value={symbol} />
      <input type="hidden" name="market" value={market} />
      <input type="hidden" name="name" value={name} />
      <input type="hidden" name="return_to" value={`/${locale}/instruments/${symbol}`} />
      <Button type="submit" variant="outline" size="sm">
        <Plus className="mr-2 h-4 w-4" />
        {t("addToWatchlist")}
      </Button>
    </form>
  );
}
