"use client";

import { TrendingUp, TrendingDown, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface Sector {
  name: string;
  name_en: string;
  change_percent: number;
  fund_flow: string;
  fund_flow_amount: number;
  leader_symbol: string;
  leader_name: string;
  leader_change_percent: number;
  symbols_count: number;
}

interface HotSectorsProps {
  sectors: Sector[];
  isLoading?: boolean;
  className?: string;
}

export function HotSectors({ sectors, isLoading = false, className = "" }: HotSectorsProps) {
  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-base">🔥 热点板块</CardTitle>
          <CardDescription className="text-xs">板块资金流向分析</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (sectors.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-base">🔥 热点板块</CardTitle>
          <CardDescription className="text-xs">板块资金流向分析</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-sm text-muted-foreground">
            暂无热点板块数据
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-base">🔥 热点板块</CardTitle>
        <CardDescription className="text-xs">
          板块资金流向分析 · Top {sectors.length}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {sectors.map((sector, index) => {
          const isPositive = sector.change_percent >= 0;
          const isFlowIn = sector.fund_flow === "流入";

          return (
            <div
              key={index}
              className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/30 transition-colors"
            >
              <div className="flex items-center gap-3 flex-1">
                <div className="text-lg font-bold text-muted-foreground w-6">
                  {index + 1}
                </div>
                
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="font-semibold text-sm">{sector.name}</h4>
                    <Badge variant="outline" className="text-xs">
                      {sector.symbols_count}只
                    </Badge>
                  </div>
                  
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span>龙头: {sector.leader_name}</span>
                    <span className={isPositive ? "text-green-600" : "text-red-600"}>
                      {isPositive ? "+" : ""}{sector.leader_change_percent.toFixed(2)}%
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex flex-col items-end gap-1">
                <div className={`flex items-center gap-1 font-semibold ${isPositive ? "text-green-600" : "text-red-600"}`}>
                  {isPositive ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                  <span>{isPositive ? "+" : ""}{sector.change_percent.toFixed(2)}%</span>
                </div>
                
                <div className={`flex items-center gap-1 text-xs ${isFlowIn ? "text-green-600" : "text-red-600"}`}>
                  {isFlowIn ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                  <span>{sector.fund_flow} {Math.abs(sector.fund_flow_amount).toFixed(1)}亿</span>
                </div>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
