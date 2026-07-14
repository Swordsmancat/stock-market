"use client";

import * as React from "react";
import { useRouter } from "@/src/i18n/routing";
import { Loader2, Search } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import { searchInstrumentAction } from "@/app/[locale]/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

type Instrument = {
  symbol: string;
  name: string;
  market: string;
};

const SEARCH_RESULT_LIMIT = 10;
const SEARCH_DEBOUNCE_MS = 250;

export function GlobalSearch() {
  const [open, setOpen] = React.useState(false);
  const [query, setQuery] = React.useState("");
  const [instruments, setInstruments] = React.useState<Instrument[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);
  const [loadError, setLoadError] = React.useState<string | null>(null);
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("TopNav");
  const searchLoadFailedMessage = t("searchLoadFailed");

  React.useEffect(() => {
    const down = (event: KeyboardEvent) => {
      if (event.key === "k" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        setOpen(true);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  React.useEffect(() => {
    const normalizedQuery = query.trim();
    if (!open || !normalizedQuery) {
      setInstruments([]);
      setIsLoading(false);
      setLoadError(null);
      return;
    }

    let active = true;
    setIsLoading(true);
    setLoadError(null);
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams({
        q: normalizedQuery,
        limit: String(SEARCH_RESULT_LIMIT),
        offset: "0",
      });
      void fetch(`/api/instruments?${params.toString()}`)
        .then(async (response) => {
          if (!response.ok) {
            throw new Error("load failed");
          }
          const data = (await response.json()) as { items?: Instrument[] };
          if (active) setInstruments(data.items ?? []);
        })
        .catch(() => {
          if (active) setLoadError(searchLoadFailedMessage);
        })
        .finally(() => {
          if (active) setIsLoading(false);
        });
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [open, query, searchLoadFailedMessage]);

  const hasQuery = query.trim().length > 0;

  return (
    <>
      <Button
        type="button"
        variant="outline"
        className="relative h-9 w-full justify-start rounded-md border bg-card text-sm font-normal text-muted-foreground shadow-sm sm:pr-12 md:w-56 lg:w-96"
        onClick={() => setOpen(true)}
      >
        <Search className="mr-2 h-4 w-4 shrink-0" />
        <span className="truncate">{t("searchPlaceholder")}</span>
        <kbd className="pointer-events-none absolute right-[0.3rem] top-[0.3rem] hidden h-6 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex">
          <span className="text-xs">⌘</span>K
        </kbd>
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="z-[200] sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{t("searchPlaceholder")}</DialogTitle>
          </DialogHeader>

          <form action={searchInstrumentAction} className="flex gap-2">
            <input type="hidden" name="locale" value={locale} />
            <Input
              name="symbol"
              value={query}
              onChange={(event) => setQuery(event.target.value.toUpperCase())}
              placeholder={t("searchInputPlaceholder")}
              autoFocus
            />
            <Button type="submit">{t("searchGo")}</Button>
          </form>

          {isLoading ? (
            <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              {t("searchLoading")}
            </div>
          ) : null}

          {loadError ? <p className="py-2 text-sm text-destructive">{loadError}</p> : null}

          {hasQuery && !isLoading && !loadError ? (
            <ul className="max-h-72 space-y-1 overflow-y-auto">
              {instruments.length === 0 ? (
                <li className="py-4 text-center text-sm text-muted-foreground">{t("noResults")}</li>
              ) : (
                instruments.map((instrument) => (
                  <li key={`${instrument.symbol}-${instrument.market}`}>
                    <button
                      type="button"
                      className="flex w-full items-center rounded-md px-3 py-2 text-left text-sm hover:bg-accent"
                      onClick={() => {
                        setOpen(false);
                        router.push(`/instruments/${instrument.symbol}` as any);
                      }}
                    >
                      <span className="font-medium">{instrument.symbol}</span>
                      <span className="ml-2 text-muted-foreground">{instrument.name}</span>
                      <span className="ml-auto text-xs text-muted-foreground">{instrument.market}</span>
                    </button>
                  </li>
                ))
              )}
            </ul>
          ) : null}
        </DialogContent>
      </Dialog>
    </>
  );
}
