import { Link } from "@/src/i18n/routing"
import { NotificationBell } from "@/components/notification-bell"
import { getLocale, getTranslations } from "next-intl/server"
import { CandlestickChart } from "lucide-react"

import { ModeToggle } from "@/components/mode-toggle"
import { LanguageSwitcher } from "@/components/language-switcher"
import { GlobalSearch } from "@/components/global-search"

export async function TopNavBar() {
  const [t, alerts, locale] = await Promise.all([
    getTranslations("TopNav"),
    getTranslations("Alerts"),
    getLocale(),
  ])

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/80 bg-background/95 shadow-[0_1px_0_hsl(var(--primary)/0.12)] backdrop-blur supports-[backdrop-filter]:bg-background/90">
      <div className="flex h-14 items-center gap-3 px-3 md:px-4">
        <div className="flex min-w-0 flex-1 items-center gap-3 md:gap-5">
          <Link
            href="/"
            className="flex min-w-0 items-center gap-2 rounded-sm px-1.5 py-1 transition-colors hover:bg-accent"
          >
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-primary/30 bg-primary/15 text-primary shadow-[0_0_18px_hsl(var(--primary)/0.18)]">
              <CandlestickChart className="h-4 w-4" />
            </span>
            <span className="hidden truncate text-sm font-semibold tracking-normal text-foreground sm:inline-block">
              {t("title")}
            </span>
          </Link>
          <div className="min-w-0 flex-1 max-w-2xl">
            <GlobalSearch
              locale={locale}
              labels={{
                placeholder: t("searchPlaceholder"),
                inputPlaceholder: t("searchInputPlaceholder"),
                go: t("searchGo"),
                loading: t("searchLoading"),
                loadFailed: t("searchLoadFailed"),
                noResults: t("noResults"),
                assetTypes: {
                  stock: t("assetTypeStock"),
                  etf: t("assetTypeEtf"),
                  index: t("assetTypeIndex"),
                },
              }}
            />
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <NotificationBell
            labels={{
              title: alerts("title"),
              recentTriggers: alerts("recentTriggers"),
              loadFailed: alerts("loadFailed"),
              noTriggers: alerts("noTriggers"),
              viewAll: alerts("viewAll"),
            }}
          />
          <LanguageSwitcher />
          <ModeToggle />
        </div>
      </div>
    </header>
  )
}
