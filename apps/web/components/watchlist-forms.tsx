import { getTranslations } from "next-intl/server";

import {
  addWatchlistItemAction,
  removeWatchlistItemAction,
  updateWatchlistAlertsAction,
} from "@/app/[locale]/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Plus, Trash2 } from "lucide-react";

type WatchlistAddFormProps = {
  locale: string;
  className?: string;
};

export async function WatchlistAddForm({ locale, className }: WatchlistAddFormProps) {
  const t = await getTranslations("Watchlist");

  return (
    <form action={addWatchlistItemAction} className={className}>
      <input type="hidden" name="locale" value={locale} />
      <div className="grid gap-2 sm:grid-cols-[7rem_6rem_minmax(10rem,1fr)_7rem_7rem_auto]">
        <Input name="symbol" placeholder={t("symbolPlaceholder")} className="sm:w-28" required />
        <Input name="market" placeholder={t("marketPlaceholder")} className="sm:w-24" required />
        <Input name="name" placeholder={t("namePlaceholder")} className="sm:w-48" />
        <Input name="price_above" type="number" step="0.01" placeholder={t("priceAbovePlaceholder")} />
        <Input name="rsi_below" type="number" step="0.01" placeholder={t("rsiBelowPlaceholder")} />
        <Button type="submit">
          <Plus className="mr-2 h-4 w-4" />
          {t("addSymbol")}
        </Button>
      </div>
    </form>
  );
}

type WatchlistRemoveButtonProps = {
  locale: string;
  symbol: string;
  market: string;
};

export async function WatchlistRemoveButton({ locale, symbol, market }: WatchlistRemoveButtonProps) {
  const t = await getTranslations("Watchlist");

  return (
    <form action={removeWatchlistItemAction}>
      <input type="hidden" name="locale" value={locale} />
      <input type="hidden" name="symbol" value={symbol} />
      <input type="hidden" name="market" value={market} />
      <Button type="submit" variant="ghost" size="icon" className="text-destructive" title={t("remove")}>
        <Trash2 className="h-4 w-4" />
        <span className="sr-only">{t("remove")}</span>
      </Button>
    </form>
  );
}

type WatchlistEditAlertRulesFormProps = {
  locale: string;
  symbol: string;
  market: string;
  name: string;
  alertRules?: Record<string, number>;
};

export async function WatchlistEditAlertRulesForm({
  locale,
  symbol,
  market,
  name,
  alertRules = {},
}: WatchlistEditAlertRulesFormProps) {
  const t = await getTranslations("Watchlist");

  return (
    <form action={updateWatchlistAlertsAction} className="flex flex-wrap items-center gap-1">
      <input type="hidden" name="locale" value={locale} />
      <input type="hidden" name="symbol" value={symbol} />
      <input type="hidden" name="market" value={market} />
      <input type="hidden" name="name" value={name} />
      <Input
        name="price_above"
        type="number"
        step="0.01"
        defaultValue={alertRules.price_above ?? ""}
        placeholder={t("priceAbovePlaceholder")}
        className="h-8 w-24"
      />
      <Input
        name="rsi_below"
        type="number"
        step="0.01"
        defaultValue={alertRules.rsi_below ?? ""}
        placeholder={t("rsiBelowPlaceholder")}
        className="h-8 w-24"
      />
      <Button type="submit" size="sm" variant="outline">
        {t("saveAlerts")}
      </Button>
    </form>
  );
}
