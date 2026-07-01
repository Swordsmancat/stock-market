"use client";

import * as React from "react";
import { Link } from "@/src/i18n/routing";
import { Bell } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

type AlertTrigger = {
  symbol: string;
  market: string;
  rule_key: string;
  threshold: number;
  triggered_at: string;
};

export function NotificationBell() {
  const [triggers, setTriggers] = React.useState<AlertTrigger[]>([]);
  const [loadError, setLoadError] = React.useState(false);
  const t = useTranslations("Alerts");

  React.useEffect(() => {
    fetch("/api/alerts/triggers/recent?limit=5")
      .then((res) => {
        if (!res.ok) {
          throw new Error("load failed");
        }
        return res.json();
      })
      .then((data) => setTriggers(data.items ?? []))
      .catch(() => {
        setTriggers([]);
        setLoadError(true);
      });
  }, []);

  const hasTriggers = triggers.length > 0;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          <span className="sr-only">{t("title")}</span>
          {hasTriggers ? (
            <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-primary" />
          ) : null}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-72">
        <DropdownMenuLabel>{t("recentTriggers")}</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {loadError ? (
          <DropdownMenuItem disabled>{t("loadFailed")}</DropdownMenuItem>
        ) : hasTriggers ? (
          triggers.map((trigger) => (
            <DropdownMenuItem key={`${trigger.symbol}-${trigger.rule_key}-${trigger.triggered_at}`} asChild>
              <Link href="/watchlist" className="flex flex-col items-start gap-0.5">
                <span className="font-medium">
                  {trigger.symbol} · {trigger.rule_key}
                </span>
                <span className="text-xs text-muted-foreground">
                  {trigger.threshold} · {new Date(trigger.triggered_at).toLocaleString()}
                </span>
              </Link>
            </DropdownMenuItem>
          ))
        ) : (
          <DropdownMenuItem disabled>{t("noTriggers")}</DropdownMenuItem>
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href="/alerts">{t("viewAll")}</Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
