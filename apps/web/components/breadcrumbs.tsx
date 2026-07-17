"use client"

import { Link, usePathname } from "@/src/i18n/routing"
import { getInstrumentDisplayName } from "@/lib/instrument-display"
import { ChevronRight, Home } from "lucide-react"
import { useLocale, useTranslations } from "next-intl"

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import React from "react"

export function Breadcrumbs() {
  const pathname = usePathname()
  const locale = useLocale()
  const t = useTranslations("Breadcrumbs")
  const navigationTranslations = useTranslations("Navigation")
  
  if (pathname === "/") {
    return null
  }

  const segments = pathname.split("/").filter(Boolean)

  function formatBreadcrumbSegment(segment: string, index: number): string {
    if (index === 0) {
      const navigationKeyBySegment: Record<string, Parameters<typeof navigationTranslations>[0]> = {
        instruments: "instruments",
        "ai-research": "aiResearch",
        evidence: "evidence",
        "market-research": "marketResearch",
        "market-movers": "marketMovers",
        storage: "storage",
        watchlist: "watchlist",
        portfolios: "portfolios",
        reports: "reports",
        alerts: "alerts",
        "task-runs": "taskRuns",
        settings: "settings",
      }
      const navigationKey = navigationKeyBySegment[segment]
      if (navigationKey !== undefined) {
        return navigationTranslations(navigationKey)
      }
    }

    if (segments[0] === "instruments" && index === 1) {
      return getInstrumentDisplayName(segment, locale)
    }

    return decodeURIComponent(segment).replace(/-/g, " ")
  }

  return (
    <Breadcrumb className="mb-4">
      <BreadcrumbList>
        <BreadcrumbItem>
          <BreadcrumbLink asChild>
            <Link href="/" className="flex items-center gap-1">
              <Home className="h-3 w-3" />
              <span className="sr-only">{t("home")}</span>
            </Link>
          </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbSeparator>
          <ChevronRight className="h-4 w-4" />
        </BreadcrumbSeparator>
        
        {segments.map((segment, index) => {
          const isLast = index === segments.length - 1
          const href = `/${segments.slice(0, index + 1).join("/")}`
          const title = formatBreadcrumbSegment(segment, index)

          return (
            <React.Fragment key={href}>
              <BreadcrumbItem>
                {isLast ? (
                  <BreadcrumbPage>{title}</BreadcrumbPage>
                ) : (
                  <BreadcrumbLink asChild>
                    <Link href={href as any}>{title}</Link>
                  </BreadcrumbLink>
                )}
              </BreadcrumbItem>
              {!isLast && (
                <BreadcrumbSeparator>
                  <ChevronRight className="h-4 w-4" />
                </BreadcrumbSeparator>
              )}
            </React.Fragment>
          )
        })}
      </BreadcrumbList>
    </Breadcrumb>
  )
}
