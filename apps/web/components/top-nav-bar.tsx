"use client"

import { Link } from "@/src/i18n/routing"
import { NotificationBell } from "@/components/notification-bell"
import { useTranslations } from "next-intl"
import { CandlestickChart } from "lucide-react"

import { Button } from "@/components/ui/button"
import { ModeToggle } from "@/components/mode-toggle"
import { LanguageSwitcher } from "@/components/language-switcher"
import { GlobalSearch } from "@/components/global-search"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

export function TopNavBar() {
  const t = useTranslations("TopNav")

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/85">
      <div className="flex h-14 items-center gap-3 px-3 md:px-5">
        <div className="flex min-w-0 flex-1 items-center gap-3 md:gap-5">
          <Link
            href="/"
            className="flex min-w-0 items-center gap-2 rounded-sm px-1.5 py-1 transition-colors hover:bg-muted"
          >
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-primary/20 bg-primary/10 text-primary">
              <CandlestickChart className="h-4 w-4" />
            </span>
            <span className="hidden truncate text-sm font-semibold tracking-normal sm:inline-block">
              {t("title")}
            </span>
          </Link>
          <div className="min-w-0 flex-1 max-w-2xl">
            <GlobalSearch />
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <NotificationBell />
          <LanguageSwitcher />
          <ModeToggle />
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="relative h-9 w-9 rounded-sm p-0">
                <Avatar className="h-8 w-8 rounded-sm">
                  <AvatarFallback>U</AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-56" align="end">
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">User</p>
                  <p className="text-xs leading-none text-muted-foreground">
                    user@example.com
                  </p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link href="/settings">{t("profile")}</Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href="/settings">{t("settings")}</Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem disabled>{t("logout")}</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  )
}
