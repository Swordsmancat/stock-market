"use client";

import { Link, usePathname } from "@/src/i18n/routing";
import { useTranslations } from "next-intl";

import { NAVIGATION_ITEMS } from "@/components/navigation-items";
import { cn } from "@/lib/utils";

export function MobileNavigation() {
  const pathname = usePathname();
  const t = useTranslations("Navigation");

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-border/80 bg-background/95 pb-[env(safe-area-inset-bottom)] shadow-[0_-1px_0_hsl(var(--primary)/0.12)] backdrop-blur md:hidden">
      <ul className="flex overflow-x-auto px-1.5 py-1 scrollbar-thin">
        {NAVIGATION_ITEMS.map((item) => {
          const isActive =
            pathname === item.href ||
            (pathname.startsWith(item.href) && item.href !== "/");
          return (
            <li key={item.href}>
              <Link
                href={item.href as any}
                className={cn(
                  "flex min-h-12 min-w-[4.6rem] flex-col items-center justify-center gap-1 rounded-sm border border-transparent px-1 py-1.5 text-[10px] transition-colors duration-200",
                  isActive ? "border-primary/30 bg-primary/15 text-primary font-medium" : "text-muted-foreground",
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
