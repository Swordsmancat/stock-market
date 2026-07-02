"use client"

import { Link, usePathname } from "@/src/i18n/routing"
import { Activity, BarChart3, Bell, Home, List, PieChart, Settings, TrendingUp } from "lucide-react"
import { useTranslations } from "next-intl"

import { cn } from "@/lib/utils"

const navItems = [
  {
    titleKey: "dashboard",
    href: "/",
    icon: Home,
  },
  {
    titleKey: "instruments",
    href: "/instruments",
    icon: TrendingUp,
  },
  {
    titleKey: "watchlist",
    href: "/watchlist",
    icon: List,
  },
  {
    titleKey: "portfolios",
    href: "/portfolios",
    icon: PieChart,
  },
  {
    titleKey: "reports",
    href: "/reports",
    icon: BarChart3,
  },
  {
    titleKey: "alerts",
    href: "/alerts",
    icon: Bell,
  },
  {
    titleKey: "taskRuns",
    href: "/task-runs",
    icon: Activity,
  },
  {
    titleKey: "settings",
    href: "/settings",
    icon: Settings,
  },
]

export function SidebarNavigation() {
  const pathname = usePathname()
  const t = useTranslations("Navigation")

  return (
    <nav className="flex flex-col gap-2 p-4 w-64 border-r h-[calc(100vh-3.5rem)] overflow-y-auto hidden md:flex">
      <div className="flex-1">
        <ul className="grid gap-1">
          {navItems.map((item, index) => {
            const isActive = pathname === item.href || (pathname.startsWith(item.href) && item.href !== "/")
            return (
              <li key={index}>
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
