import { Activity, BarChart3, Bell, Home, List, PieChart, Settings, TrendingUp } from "lucide-react";

export const NAVIGATION_ITEMS = [
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
] as const;

export type NavigationItem = (typeof NAVIGATION_ITEMS)[number];
