import { Activity, BookOpenText, BrainCircuit, ChartNoAxesCombined, Database, Home, List, ListOrdered, Settings, TrendingUp, type LucideIcon } from "lucide-react";

export type NavigationItem = {
  titleKey: string;
  href: string;
  icon: LucideIcon;
  mobile?: boolean;
};

export const NAVIGATION_ITEMS: readonly NavigationItem[] = [
  {
    titleKey: "dashboard",
    href: "/",
    icon: Home,
  },
  {
    titleKey: "aiResearch",
    href: "/ai-research",
    icon: BrainCircuit,
  },
  {
    titleKey: "instruments",
    href: "/instruments",
    icon: TrendingUp,
  },
  {
    titleKey: "marketResearch",
    href: "/market-research",
    icon: ChartNoAxesCombined,
    mobile: false,
  },
  {
    titleKey: "topicResearch",
    href: "/topic-research",
    icon: BookOpenText,
    mobile: false,
  },
  {
    titleKey: "marketMovers",
    href: "/market-movers",
    icon: ListOrdered,
    mobile: false,
  },
  {
    titleKey: "storage",
    href: "/storage",
    icon: Database,
    mobile: false,
  },
  {
    titleKey: "crawlerMonitor",
    href: "/crawler-monitor",
    icon: Activity,
    mobile: false,
  },
  {
    titleKey: "watchlist",
    href: "/watchlist",
    icon: List,
  },
  {
    titleKey: "settings",
    href: "/settings",
    icon: Settings,
  },
];
