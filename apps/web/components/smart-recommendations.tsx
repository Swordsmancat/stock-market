"use client";

import { TrendingUp, Activity, AlertCircle, Zap } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";

interface Recommendation {
  symbol: string;
  type: "breakout" | "volume_anomaly" | "oversold_rebound" | "strong_momentum";
  title: string;
  reason: string;
  confidence: number;
  timestamp: string;
  data: Record<string, any>;
}

interface SmartRecommendationsProps {
  recommendations: Recommendation[];
  isLoading?: boolean;
  className?: string;
}

const typeConfig = {
  breakout: {
    icon: TrendingUp,
    label: "突破",
    color: "text-blue-600",
    bgColor: "bg-blue-50",
  },
  volume_anomaly: {
    icon: Activity,
    label: "成交异常",
    color: "text-purple-600",
    bgColor: "bg-purple-50",
  },
  oversold_rebound: {
    icon: AlertCircle,
    label: "超跌反弹",
    color: "text-orange-600",
    bgColor: "bg-orange-50",
  },
  strong_momentum: {
    icon: Zap,
    label: "强势",
    color: "text-green-600",
    bgColor: "bg-green-50",
  },
};

export function SmartRecommendations({
  recommendations,
  isLoading = false,
  className = "",
}: SmartRecommendationsProps) {
  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-base">📈 今日推荐</CardTitle>
          <CardDescription className="text-xs">基于技术分析的智能推荐</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (recommendations.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-base">📈 今日推荐</CardTitle>
          <CardDescription className="text-xs">基于技术分析的智能推荐</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-sm text-muted-foreground">
            暂无推荐,继续监控市场中...
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-base">📈 今日推荐</CardTitle>
        <CardDescription className="text-xs">
          基于技术分析的智能推荐 · {recommendations.length} 条
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-[400px]">
          <div className="space-y-3 p-4">
            {recommendations.map((rec, index) => {
              const config = typeConfig[rec.type];
              const Icon = config.icon;
              const confidencePercent = Math.round(rec.confidence * 100);

              return (
                <div
                  key={index}
                  className="flex gap-3 p-3 rounded-lg border hover:bg-muted/30 transition-colors"
                >
                  <div className={`flex-shrink-0 w-10 h-10 rounded-full ${config.bgColor} flex items-center justify-center`}>
                    <Icon className={`h-5 w-5 ${config.color}`} />
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <h4 className="font-semibold text-sm">{rec.title}</h4>
                      <Badge variant="secondary" className="text-xs flex-shrink-0">
                        {config.label}
                      </Badge>
                    </div>
                    
                    <p className="text-xs text-muted-foreground mb-2">
                      {rec.reason}
                    </p>
                    
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-muted-foreground">
                        置信度: {confidencePercent}%
                      </span>
                      <span className="text-muted-foreground">•</span>
                      <span className="text-muted-foreground">
                        {new Date(rec.timestamp).toLocaleDateString("zh-CN")}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
