"use client";

import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface RefreshIndicatorProps {
  lastUpdated: Date | null;
  timeAgo: string;
  isRefreshing: boolean;
  onRefresh: () => void;
  enabled: boolean;
  onToggleEnabled: () => void;
  className?: string;
}

export function RefreshIndicator({
  lastUpdated,
  timeAgo,
  isRefreshing,
  onRefresh,
  enabled,
  onToggleEnabled,
  className,
}: RefreshIndicatorProps) {
  return (
    <div className={cn("flex items-center gap-2 text-xs text-muted-foreground", className)}>
      <Button
        variant="ghost"
        size="sm"
        onClick={onRefresh}
        disabled={isRefreshing}
        className="h-7 px-2"
      >
        <RefreshCw className={cn("h-3.5 w-3.5", isRefreshing && "animate-spin")} />
        <span className="ml-1.5">刷新</span>
      </Button>
      
      {lastUpdated && (
        <span className="text-xs">
          最后更新: {timeAgo}
        </span>
      )}
      
      <Button
        variant="outline"
        size="sm"
        onClick={onToggleEnabled}
        className="h-7 px-2"
      >
        {enabled ? "停止自动刷新" : "开启自动刷新"}
      </Button>
    </div>
  );
}
