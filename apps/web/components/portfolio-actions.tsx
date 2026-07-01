"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Plus, Trash2, Pencil } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type PortfolioAddPositionFormProps = {
  portfolioId: string;
  className?: string;
};

export function PortfolioAddPositionForm({ portfolioId, className }: PortfolioAddPositionFormProps) {
  const [isPending, startTransition] = React.useTransition();
  const [message, setMessage] = React.useState<string | null>(null);
  const router = useRouter();
  const t = useTranslations("Portfolios");

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const symbol = String(formData.get("symbol") ?? "").trim().toUpperCase();
    const market = String(formData.get("market") ?? "").trim().toUpperCase();
    const name = String(formData.get("name") ?? "").trim();
    const quantity = Number(formData.get("quantity"));
    const avgCost = Number(formData.get("avg_cost"));

    if (!symbol || !market || !Number.isFinite(quantity) || !Number.isFinite(avgCost)) {
      setMessage(t("operationFailed"));
      return;
    }

    startTransition(async () => {
      setMessage(null);
      const response = await fetch(`/api/portfolios/${portfolioId}/positions`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          symbol,
          market,
          name: name || null,
          quantity,
          avg_cost: avgCost,
        }),
      });

      if (!response.ok) {
        setMessage(t("operationFailed"));
        return;
      }

      form.reset();
      setMessage(t("addPositionSuccess"));
      router.refresh();
    });
  }

  return (
    <form className={className} onSubmit={handleSubmit}>
      <div className="grid gap-2 sm:grid-cols-[7rem_6rem_minmax(10rem,1fr)_7rem_7rem_auto]">
        <Input name="symbol" placeholder={t("symbolPlaceholder")} className="sm:w-28" />
        <Input name="market" placeholder={t("marketPlaceholder")} className="sm:w-24" />
        <Input name="name" placeholder={t("namePlaceholder")} className="sm:w-48" />
        <Input name="quantity" type="number" step="0.0001" placeholder={t("quantityPlaceholder")} />
        <Input name="avg_cost" type="number" step="0.01" placeholder={t("avgCostPlaceholder")} />
        <Button type="submit" disabled={isPending}>
          <Plus className="mr-2 h-4 w-4" />
          {isPending ? t("addingPosition") : t("addPosition")}
        </Button>
      </div>
      {message ? <p className="mt-2 text-sm text-muted-foreground">{message}</p> : null}
    </form>
  );
}

type PortfolioRemovePositionButtonProps = {
  portfolioId: string;
  symbol: string;
  market: string;
};

export function PortfolioRemovePositionButton({
  portfolioId,
  symbol,
  market,
}: PortfolioRemovePositionButtonProps) {
  const [isPending, startTransition] = React.useTransition();
  const router = useRouter();
  const t = useTranslations("Portfolios");

  function handleRemove() {
    startTransition(async () => {
      const params = new URLSearchParams({ symbol, market });
      const response = await fetch(
        `/api/portfolios/${portfolioId}/positions?${params.toString()}`,
        { method: "DELETE" },
      );
      if (response.ok) {
        router.refresh();
      }
    });
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      className="text-destructive"
      title={t("removePosition")}
      disabled={isPending}
      onClick={handleRemove}
    >
      <Trash2 className="h-4 w-4" />
      <span className="sr-only">{isPending ? t("removingPosition") : t("removePosition")}</span>
    </Button>
  );
}

type PortfolioCreateFormProps = {
  className?: string;
};

export function PortfolioCreateForm({ className }: PortfolioCreateFormProps) {
  const [isPending, startTransition] = React.useTransition();
  const [message, setMessage] = React.useState<string | null>(null);
  const router = useRouter();
  const t = useTranslations("Portfolios");

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const name = String(formData.get("name") ?? "").trim();
    const baseCurrency = String(formData.get("base_currency") ?? "USD").trim().toUpperCase();

    if (!name) {
      setMessage(t("operationFailed"));
      return;
    }

    startTransition(async () => {
      setMessage(null);
      const response = await fetch("/api/portfolios", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ name, base_currency: baseCurrency }),
      });

      if (!response.ok) {
        setMessage(t("operationFailed"));
        return;
      }

      form.reset();
      setMessage(t("createSuccess"));
      router.refresh();
    });
  }

  return (
    <form className={className} onSubmit={handleSubmit}>
      <div className="flex flex-wrap gap-2">
        <Input name="name" placeholder={t("portfolioNamePlaceholder")} className="w-48" />
        <Input name="base_currency" placeholder={t("baseCurrencyPlaceholder")} className="w-28" />
        <Button type="submit" disabled={isPending}>
          <Plus className="mr-2 h-4 w-4" />
          {isPending ? t("creatingPortfolio") : t("createPortfolio")}
        </Button>
      </div>
      {message ? <p className="mt-2 text-sm text-muted-foreground">{message}</p> : null}
    </form>
  );
}

type PortfolioRenameFormProps = {
  portfolioId: string;
  currentName: string;
  isDefault?: boolean;
};

export function PortfolioRenameForm({ portfolioId, currentName, isDefault }: PortfolioRenameFormProps) {
  const [isPending, startTransition] = React.useTransition();
  const [message, setMessage] = React.useState<string | null>(null);
  const router = useRouter();
  const t = useTranslations("Portfolios");

  if (isDefault) {
    return null;
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const name = String(formData.get("name") ?? "").trim();
    if (!name) {
      setMessage(t("operationFailed"));
      return;
    }

    startTransition(async () => {
      setMessage(null);
      const response = await fetch(`/api/portfolios/${portfolioId}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (!response.ok) {
        setMessage(t("operationFailed"));
        return;
      }
      setMessage(t("renameSuccess"));
      router.refresh();
    });
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap items-center gap-2">
      <Input name="name" defaultValue={currentName} className="w-48" />
      <Button type="submit" variant="outline" size="sm" disabled={isPending}>
        <Pencil className="mr-2 h-4 w-4" />
        {isPending ? t("renamingPortfolio") : t("renamePortfolio")}
      </Button>
      {message ? <p className="w-full text-sm text-muted-foreground">{message}</p> : null}
    </form>
  );
}

type PortfolioDeleteButtonProps = {
  portfolioId: string;
  isDefault?: boolean;
};

export function PortfolioDeleteButton({ portfolioId, isDefault }: PortfolioDeleteButtonProps) {
  const [isPending, startTransition] = React.useTransition();
  const router = useRouter();
  const t = useTranslations("Portfolios");

  if (isDefault) {
    return null;
  }

  function handleDelete() {
    startTransition(async () => {
      const response = await fetch(`/api/portfolios/${portfolioId}`, { method: "DELETE" });
      if (response.ok) {
        router.push("/portfolios?portfolio=demo");
        router.refresh();
      }
    });
  }

  return (
    <Button variant="destructive" size="sm" disabled={isPending} onClick={handleDelete}>
      <Trash2 className="mr-2 h-4 w-4" />
      {isPending ? t("deletingPortfolio") : t("deletePortfolio")}
    </Button>
  );
}
