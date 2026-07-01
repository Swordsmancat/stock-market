import { getTranslations } from "next-intl/server";
import { Pencil, Plus, Trash2 } from "lucide-react";

import {
  addPortfolioPositionAction,
  createPortfolioAction,
  deletePortfolioAction,
  removePortfolioPositionAction,
  renamePortfolioAction,
} from "@/app/[locale]/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type PortfolioCreateFormProps = {
  locale: string;
  className?: string;
};

export async function PortfolioCreateForm({ locale, className }: PortfolioCreateFormProps) {
  const t = await getTranslations("Portfolios");

  return (
    <form action={createPortfolioAction} className={className}>
      <input type="hidden" name="locale" value={locale} />
      <div className="flex flex-wrap gap-2">
        <Input name="name" placeholder={t("portfolioNamePlaceholder")} className="w-48" required />
        <Input name="base_currency" placeholder={t("baseCurrencyPlaceholder")} className="w-28" defaultValue="USD" />
        <Button type="submit">
          <Plus className="mr-2 h-4 w-4" />
          {t("createPortfolio")}
        </Button>
      </div>
    </form>
  );
}

type PortfolioAddPositionFormProps = {
  locale: string;
  portfolioId: string;
  className?: string;
};

export async function PortfolioAddPositionForm({ locale, portfolioId, className }: PortfolioAddPositionFormProps) {
  const t = await getTranslations("Portfolios");

  return (
    <form action={addPortfolioPositionAction} className={className}>
      <input type="hidden" name="locale" value={locale} />
      <input type="hidden" name="portfolio_id" value={portfolioId} />
      <div className="grid gap-2 sm:grid-cols-[7rem_6rem_minmax(10rem,1fr)_7rem_7rem_auto]">
        <Input name="symbol" placeholder={t("symbolPlaceholder")} className="sm:w-28" required />
        <Input name="market" placeholder={t("marketPlaceholder")} className="sm:w-24" required />
        <Input name="name" placeholder={t("namePlaceholder")} className="sm:w-48" />
        <Input name="quantity" type="number" step="0.0001" placeholder={t("quantityPlaceholder")} required />
        <Input name="avg_cost" type="number" step="0.01" placeholder={t("avgCostPlaceholder")} required />
        <Button type="submit">
          <Plus className="mr-2 h-4 w-4" />
          {t("addPosition")}
        </Button>
      </div>
    </form>
  );
}

type PortfolioRemovePositionButtonProps = {
  locale: string;
  portfolioId: string;
  symbol: string;
  market: string;
};

export async function PortfolioRemovePositionButton({
  locale,
  portfolioId,
  symbol,
  market,
}: PortfolioRemovePositionButtonProps) {
  const t = await getTranslations("Portfolios");

  return (
    <form action={removePortfolioPositionAction}>
      <input type="hidden" name="locale" value={locale} />
      <input type="hidden" name="portfolio_id" value={portfolioId} />
      <input type="hidden" name="symbol" value={symbol} />
      <input type="hidden" name="market" value={market} />
      <Button type="submit" variant="ghost" size="icon" className="text-destructive" title={t("removePosition")}>
        <Trash2 className="h-4 w-4" />
        <span className="sr-only">{t("removePosition")}</span>
      </Button>
    </form>
  );
}

type PortfolioRenameFormProps = {
  locale: string;
  portfolioId: string;
  currentName: string;
  isDefault?: boolean;
};

export async function PortfolioRenameForm({
  locale,
  portfolioId,
  currentName,
  isDefault,
}: PortfolioRenameFormProps) {
  const t = await getTranslations("Portfolios");
  if (isDefault) {
    return null;
  }

  return (
    <form action={renamePortfolioAction} className="flex flex-wrap items-center gap-2">
      <input type="hidden" name="locale" value={locale} />
      <input type="hidden" name="portfolio_id" value={portfolioId} />
      <Input name="name" defaultValue={currentName} className="w-48" required />
      <Button type="submit" variant="outline" size="sm">
        <Pencil className="mr-2 h-4 w-4" />
        {t("renamePortfolio")}
      </Button>
    </form>
  );
}

type PortfolioDeleteButtonProps = {
  locale: string;
  portfolioId: string;
  isDefault?: boolean;
};

export async function PortfolioDeleteButton({ locale, portfolioId, isDefault }: PortfolioDeleteButtonProps) {
  const t = await getTranslations("Portfolios");
  if (isDefault) {
    return null;
  }

  return (
    <form action={deletePortfolioAction}>
      <input type="hidden" name="locale" value={locale} />
      <input type="hidden" name="portfolio_id" value={portfolioId} />
      <Button type="submit" variant="destructive" size="sm">
        <Trash2 className="mr-2 h-4 w-4" />
        {t("deletePortfolio")}
      </Button>
    </form>
  );
}
