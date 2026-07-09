"use client"

import { Link, usePathname } from "@/src/i18n/routing"
import { useTranslations } from "next-intl"

import { NAVIGATION_ITEMS } from "@/components/navigation-items"
import { cn } from "@/lib/utils"

export function SidebarNavigation() {
  const pathname = usePathname()
  const t = useTranslations("Navigation")

  return (
    <nav className="hidden h-[calc(100dvh-3.5rem)] w-56 shrink-0 flex-col overflow-y-auto border-r border-border/80 bg-background/95 p-2 shadow-[1px_0_0_hsl(var(--primary)/0.08)] md:flex">
      <div className="flex-1">
        <ul className="grid gap-1">
          {NAVIGATION_ITEMS.map((item) => {
            const isActive = pathname === item.href || (pathname.startsWith(item.href) && item.href !== "/")
            return (
              <li key={item.href}>
                <Link
                  href={item.href as any}
                  className={cn(
                    "group relative flex min-h-9 items-center gap-3 rounded-sm border border-transparent px-3 py-2 text-sm transition-colors duration-200 hover:border-primary/20 hover:bg-accent hover:text-foreground",
                    isActive ? "border-primary/30 bg-primary/15 text-primary font-medium shadow-[inset_0_0_0_1px_hsl(var(--primary)/0.08)]" : "text-muted-foreground"
                  )}
                >
                  {isActive ? <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-primary shadow-[0_0_10px_hsl(var(--primary)/0.55)]" /> : null}
                  <item.icon className={cn("h-4 w-4", isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground")} />
                  <span className="truncate">{t(item.titleKey as any)}</span>
                </Link>
              </li>
            )
          })}
        </ul>
      </div>
    </nav>
  )
}
