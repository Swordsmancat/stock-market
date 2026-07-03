"use client";

import { useEffect, useRef, useState } from "react";

interface UseAutoRefreshOptions {
  enabled?: boolean;
  interval?: number; // milliseconds
  onRefresh?: () => void | Promise<void>;
}

interface UseAutoRefreshReturn {
  lastUpdated: Date | null;
  timeAgo: string;
  isRefreshing: boolean;
  refresh: () => Promise<void>;
  toggleEnabled: () => void;
  setInterval: (ms: number) => void;
  enabled: boolean;
}

export function useAutoRefresh({
  enabled = true,
  interval = 30000, // 30 seconds default
  onRefresh,
}: UseAutoRefreshOptions = {}): UseAutoRefreshReturn {
  const [isEnabled, setIsEnabled] = useState(enabled);
  const [refreshInterval, setRefreshInterval] = useState(interval);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [timeAgo, setTimeAgo] = useState("--");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const refresh = async () => {
    if (isRefreshing) return;
    
    setIsRefreshing(true);
    try {
      if (onRefresh) {
        await onRefresh();
      }
      setLastUpdated(new Date());
    } finally {
      setIsRefreshing(false);
    }
  };

  const toggleEnabled = () => {
    setIsEnabled((prev) => !prev);
  };

  const updateInterval = (ms: number) => {
    setRefreshInterval(ms);
  };

  // Update "time ago" display
  useEffect(() => {
    if (!lastUpdated) return;

    const updateTimeAgo = () => {
      const now = new Date();
      const diffMs = now.getTime() - lastUpdated.getTime();
      const diffSec = Math.floor(diffMs / 1000);

      if (diffSec < 60) {
        setTimeAgo(`${diffSec}秒前`);
      } else if (diffSec < 3600) {
        const minutes = Math.floor(diffSec / 60);
        setTimeAgo(`${minutes}分钟前`);
      } else {
        const hours = Math.floor(diffSec / 3600);
        setTimeAgo(`${hours}小时前`);
      }
    };

    updateTimeAgo();
    const timer = setInterval(updateTimeAgo, 1000);

    return () => clearInterval(timer);
  }, [lastUpdated]);

  // Auto refresh timer
  useEffect(() => {
    if (!isEnabled) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    // Initial refresh
    if (!lastUpdated) {
      refresh();
    }

    // Set up interval
    intervalRef.current = setInterval(() => {
      refresh();
    }, refreshInterval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [isEnabled, refreshInterval]);

  return {
    lastUpdated,
    timeAgo,
    isRefreshing,
    refresh,
    toggleEnabled,
    setInterval: updateInterval,
    enabled: isEnabled,
  };
}
