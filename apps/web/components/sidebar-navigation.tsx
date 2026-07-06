"use client"

import { Link, usePathname } from "@/src/i18n/routing"
import { useTranslations } from "next-intl"

import { NAVIGATION_ITEMS } from "@/components/navigation-items"
import { cn } from "@/lib/utils"

export function SidebarNavigation() {
  const pathname = usePathname()
  const t = useTranslations("Navigation")

  return (
    <nav className="flex flex-col gap-2 p-4 w-64 border-r h-[calc(100vh-3.5rem)] overflow-y-auto hidden md:flex">
      <div className="flex-1">
        <ul className="grid gap-1">
          {NAVIGATION_ITEMS.map((item) => {
            const isActive = pathname === item.href || (pathname.startsWith(item.href) && item.href !== "/")
            return (
              <li key={item.href}>
                <Link
                  href={item.href as any}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all hover:bg-accent hover:text-accent-foreground",
                    isActive ? "bg-accent text-accent-foreground font-medium" : "text-muted-foreground"
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  {t(item.titleKey as any)}
                </Link>
              </li>
            )
          })}
        </ul>
      </div>
    </nav>
  )
}
