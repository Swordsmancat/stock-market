"use client";

import { Link, usePathname } from "@/src/i18n/routing";
import { useTranslations } from "next-intl";

import { NAVIGATION_ITEMS } from "@/components/navigation-items";
import { cn } from "@/lib/utils";

export function MobileNavigation() {
  const pathname = usePathname();
  const t = useTranslations("Navigation");

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t bg-background md:hidden">
      <ul className="flex overflow-x-auto px-1">
        {NAVIGATION_ITEMS.map((item) => {
          const isActive =
            pathname === item.href ||
            (pathname.startsWith(item.href) && item.href !== "/");
          return (
            <li key={item.href}>
              <Link
                href={item.href as any}
                className={cn(
                  "flex min-w-[4.25rem] flex-col items-center gap-1 px-1 py-2 text-[10px]",
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
