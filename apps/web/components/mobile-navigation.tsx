"use client";

import { Link, usePathname } from "@/src/i18n/routing";
import { Activity, BarChart3, Bell, Home, List, PieChart, Settings, TrendingUp } from "lucide-react";
import { useTranslations } from "next-intl";

import { cn } from "@/lib/utils";

const navItems = [
  { titleKey: "dashboard", href: "/", icon: Home },
  { titleKey: "instruments", href: "/instruments", icon: TrendingUp },
  { titleKey: "watchlist", href: "/watchlist", icon: List },
  { titleKey: "portfolios", href: "/portfolios", icon: PieChart },
  { titleKey: "reports", href: "/reports", icon: BarChart3 },
  { titleKey: "alerts", href: "/alerts", icon: Bell },
  { titleKey: "settings", href: "/settings", icon: Settings },
] as const;

export function MobileNavigation() {
  const pathname = usePathname();
  const t = useTranslations("Navigation");

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t bg-background md:hidden">
      <ul className="grid grid-cols-7">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (pathname.startsWith(item.href) && item.href !== "/");
          return (
            <li key={item.href}>
              <Link
                href={item.href as any}
                className={cn(
                  "flex flex-col items-center gap-1 px-1 py-2 text-[10px]",
                  isActive ? "text-foreground font-medium" : "text-muted-foreground",
                )}
              >
                <item.icon className="h-4 w-4" />
                <span className="truncate">{t(item.titleKey as any)}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
