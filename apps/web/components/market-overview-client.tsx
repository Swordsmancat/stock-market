"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import useSWR from "swr";
import { useAutoRefresh } from "@/hooks/use-auto-refresh";
import { useKeyboardShortcuts } from "@/hooks/use-keyboard-shortcuts";
import { RefreshIndicator } from "@/components/refresh-indicator";
import { PriceChangeBadge } from "@/components/price-change-badge";
import { IndexQuickActions } from "@/components/index-quick-actions";
import { KeyboardShortcutsHelp } from "@/components/keyboard-shortcuts-help";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { MiniPriceChart } from "@/components/mini-price-chart";

type MarketOverviewData = {
  generated_at: string;
  provider: string;
  indices: {
    items: Array<{
      code: string;
      name: string;
      name_zh?: string;
      region: string;
      market: string;
      status: string;
      freshness: string;
      latest: {
        close: number | null;
        movement: {
          absolute_change: number | null;
          percent_change: number | null;
        } | null;
      } | null;
      bars: Array<any>;
    }>;
  };
};

interface MarketOverviewClientProps {
  initialData: MarketOverviewData;
  provider: string;
  locale: string;
  labels: {
    coreIndicesTitle: string;
    coreIndicesDesc: string;
    indexName: string;
    change: string;
    changePercent: string;
    trend: string;
    status: string;
  };
}

const fetcher = async (url: string) => {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch");
  return res.json();
};

export function MarketOverviewClient({
  initialData,
  provider,
  locale,
  labels,
}: MarketOverviewClientProps) {
  const router = useRouter();
  const [showShortcutsHelp, setShowShortcutsHelp] = useState(false);
  
  const { data, mutate, isValidating } = useSWR<MarketOverviewData>(
    `/api/market-overview?provider=${provider}`,
    fetcher,
    {
      fallbackData: initialData,
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
    }
  );

  const { lastUpdated, timeAgo, isRefreshing, refresh, toggleEnabled, enabled } = useAutoRefresh({
    enabled: true,
    interval: 30000,
    onRefresh: async () => {
      await mutate();
      router.refresh();
    },
  });

  // 键盘快捷键
  useKeyboardShortcuts({
    shortcuts: [
      {
        key: "r",
        handler: refresh,
        description: "刷新市场数据",
      },
      {
        key: "?",
        handler: () => setShowShortcutsHelp(true),
        description: "显示快捷键帮助",
      },
    ],
    enabled: true,
  });

  const indices = data?.indices?.items ?? [];

  return (
    <div className="space-y-4">
      <KeyboardShortcutsHelp
        open={showShortcutsHelp}
        onOpenChange={setShowShortcutsHelp}
      />
      
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">{labels.coreIndicesTitle}</h3>
          <p className="text-sm text-muted-foreground">{labels.coreIndicesDesc}</p>
        </div>
        <RefreshIndicator
          lastUpdated={lastUpdated}
          timeAgo={timeAgo}
          isRefreshing={isRefreshing || isValidating}
          onRefresh={refresh}
          enabled={enabled}
          onToggleEnabled={toggleEnabled}
        />
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[200px]">{labels.indexName}</TableHead>
                <TableHead className="text-right">最新价</TableHead>
                <TableHead className="text-right">{labels.change}</TableHead>
                <TableHead className="text-right">{labels.changePercent}</TableHead>
                <TableHead className="w-[120px]">{labels.trend}</TableHead>
                <TableHead className="text-center">{labels.status}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {indices.map((item) => {
                const displayName = locale === 'zh' ? (item.name_zh || item.name) : item.name;
                const percentChange = item.latest?.movement?.percent_change ?? null;
                const absoluteChange = item.latest?.movement?.absolute_change ?? null;
                const close = item.latest?.close ?? null;
                const hasData = item.bars && item.bars.length > 0;

                return (
                  <TableRow key={item.code} className="group border-border hover:bg-muted/30">
                    <TableCell className="font-medium">
                      <div className="flex items-center justify-between">
                        <div className="flex flex-col">
                          <span>{displayName}</span>
                          <span className="text-xs text-muted-foreground">{item.region}</span>
                        </div>
                        <IndexQuickActions
                          code={item.code}
                          name={displayName}
                        />
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {close !== null ? close.toFixed(2) : "--"}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {absoluteChange !== null ? (
                        <span className={absoluteChange >= 0 ? "text-green-600" : "text-red-600"}>
                          {absoluteChange >= 0 ? "+" : ""}{absoluteChange.toFixed(2)}
                        </span>
                      ) : (
                        "--"
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <PriceChangeBadge
                        percentChange={percentChange}
                        absoluteChange={absoluteChange}
                        marketType={item.region as "CN" | "HK" | "US"}
                        showArrow
                      />
                    </TableCell>
                    <TableCell>
                      {hasData ? (
                        <MiniPriceChart
                          items={item.bars}
                          className="h-10 w-24"
                        />
                      ) : (
                        <span className="text-xs text-muted-foreground">--</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge variant={item.freshness === "fresh" ? "secondary" : "outline"}>
                        {item.status}
                      </Badge>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
