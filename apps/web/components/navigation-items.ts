import { BrainCircuit, ChartNoAxesCombined, Home, List, Settings, TrendingUp, type LucideIcon } from "lucide-react";

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
