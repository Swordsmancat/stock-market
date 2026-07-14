import { BrainCircuit, Home, List, Settings, TrendingUp } from "lucide-react";

export const NAVIGATION_ITEMS = [
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
    titleKey: "watchlist",
    href: "/watchlist",
    icon: List,
  },
  {
    titleKey: "settings",
    href: "/settings",
    icon: Settings,
  },
] as const;

export type NavigationItem = (typeof NAVIGATION_ITEMS)[number];
