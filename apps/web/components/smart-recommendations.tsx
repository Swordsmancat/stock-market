"use client";

import { Link } from "@/src/i18n/routing";
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

type RecommendationDiagnostic = {
  source?: string | null;
  status?: string | null;
  severity?: string | null;
  code?: string | null;
  message?: string | null;
  category?: string | null;
  provider?: string | null;
};

export type SmartRecommendationsLabels = {
  title: string;
  description: string;
  loadingMessage: string;
  emptyMessage: string;
  safetyNotice: string;
  diagnosticsTitle: string;
  confidence: string;
  sourceStatus: string;
  sourceProvider: string;
  source: string;
  generatedAt: string;
  signalBreakout: string;
  signalVolumeAnomaly: string;
  signalOversoldRebound: string;
  signalStrongMomentum: string;
  signalUnknown: string;
};

interface SmartRecommendationsProps {
  recommendations: Recommendation[];
  labels: SmartRecommendationsLabels;
  locale: string;
  getInstrumentHref?: (symbol: string) => string;
  status?: string | null;
  generatedAt?: string | null;
  source?: string | null;
  provider?: string | null;
  diagnostics?: RecommendationDiagnostic[];
  isLoading?: boolean;
  className?: string;
}

function buildRecommendationSourceDetails({
  status,
  generatedAt,
  source,
  provider,
  labels,
}: Pick<SmartRecommendationsProps, "status" | "generatedAt" | "source" | "provider" | "labels">): string[] {
  const details: string[] = [];
  if (status) {
    details.push(`${labels.sourceStatus}: ${status}`);
  }
  if (provider) {
    details.push(`${labels.sourceProvider}: ${provider}`);
  }
  if (source) {
    details.push(`${labels.source}: ${source}`);
  }
  if (generatedAt) {
    details.push(`${labels.generatedAt}: ${generatedAt}`);
  }
  return details;
}

function getDiagnosticLabel(diagnostic: RecommendationDiagnostic, index: number): string {
  return diagnostic.code ?? diagnostic.category ?? diagnostic.status ?? `diagnostic_${index + 1}`;
}

const typeConfig = {
  breakout: {
    icon: TrendingUp,
    color: "text-blue-600",
    bgColor: "bg-blue-50",
  },
  volume_anomaly: {
    icon: Activity,
    color: "text-purple-600",
    bgColor: "bg-purple-50",
  },
  oversold_rebound: {
    icon: AlertCircle,
    color: "text-orange-600",
    bgColor: "bg-orange-50",
  },
  strong_momentum: {
    icon: Zap,
    color: "text-green-600",
    bgColor: "bg-green-50",
  },
};

function getSignalLabel(type: Recommendation["type"], labels: SmartRecommendationsLabels): string {
  switch (type) {
    case "breakout":
      return labels.signalBreakout;
    case "volume_anomaly":
      return labels.signalVolumeAnomaly;
    case "oversold_rebound":
      return labels.signalOversoldRebound;
    case "strong_momentum":
      return labels.signalStrongMomentum;
    default:
      return labels.signalUnknown;
  }
}

function getDateLocale(locale: string): string {
  return locale.startsWith("zh") ? "zh-CN" : "en-US";
}

export function SmartRecommendations({
  recommendations,
  labels,
  locale,
  getInstrumentHref,
  status,
  generatedAt,
  source,
  provider,
  diagnostics = [],
  isLoading = false,
  className = "",
}: SmartRecommendationsProps) {
  const sourceDetails = buildRecommendationSourceDetails({ status, generatedAt, source, provider, labels });
  const dateLocale = getDateLocale(locale);

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <TrendingUp className="h-4 w-4" aria-hidden="true" />
            {labels.title}
          </CardTitle>
          <CardDescription className="text-xs">{labels.description}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            <span className="sr-only">{labels.loadingMessage}</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (recommendations.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <TrendingUp className="h-4 w-4" aria-hidden="true" />
            {labels.title}
          </CardTitle>
          <CardDescription className="text-xs">{labels.description}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-sm text-muted-foreground">
            {labels.emptyMessage}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <TrendingUp className="h-4 w-4" aria-hidden="true" />
          {labels.title}
        </CardTitle>
        <CardDescription className="text-xs">{labels.description}</CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <div className="mx-4 mb-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          {labels.safetyNotice}
        </div>
        {sourceDetails.length > 0 ? (
          <div className="mx-4 mb-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
            {sourceDetails.map((detail) => (
              <Badge key={detail} variant="outline" className="font-normal">
                {detail}
              </Badge>
            ))}
          </div>
        ) : null}
        {diagnostics.length > 0 ? (
          <div className="mx-4 mb-3 space-y-1 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
            <div className="font-medium text-slate-900">{labels.diagnosticsTitle}</div>
            {diagnostics.map((diagnostic, index) => (
              <div key={`${getDiagnosticLabel(diagnostic, index)}-${index}`}>
                <span className="font-medium">{getDiagnosticLabel(diagnostic, index)}</span>
                {diagnostic.provider ? <span> · {labels.sourceProvider}: {diagnostic.provider}</span> : null}
                {diagnostic.source ? <span> · {labels.source}: {diagnostic.source}</span> : null}
                {diagnostic.message ? <span> · {diagnostic.message}</span> : null}
              </div>
            ))}
          </div>
        ) : null}
        <ScrollArea className="h-[400px]">
          <div className="space-y-3 p-4">
            {recommendations.map((rec, index) => {
              const config = typeConfig[rec.type as keyof typeof typeConfig] ?? typeConfig.strong_momentum;
              const Icon = config.icon;
              const confidencePercent = Math.round(rec.confidence * 100);
              const instrumentHref = getInstrumentHref?.(rec.symbol) ?? `/instruments/${encodeURIComponent(rec.symbol)}`;
              const signalLabel = getSignalLabel(rec.type, labels);

              return (
                <Link
                  key={`${rec.symbol}-${rec.type}-${rec.timestamp}-${index}`}
                  href={instrumentHref as any}
                  className="flex gap-3 p-3 rounded-lg border hover:bg-muted/30 transition-colors"
                >
                  <div className={`flex-shrink-0 w-10 h-10 rounded-full ${config.bgColor} flex items-center justify-center`}>
                    <Icon className={`h-5 w-5 ${config.color}`} />
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <h4 className="font-semibold text-sm">{rec.title}</h4>
                      <Badge variant="secondary" className="text-xs flex-shrink-0">
                        {signalLabel}
                      </Badge>
                    </div>
                    
                    <p className="text-xs text-muted-foreground mb-2">
                      {rec.reason}
                    </p>
                    
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-muted-foreground">
                        {labels.confidence}: {confidencePercent}%
                      </span>
                      <span className="text-muted-foreground">•</span>
                      <span className="text-muted-foreground">
                        {new Date(rec.timestamp).toLocaleDateString(dateLocale)}
                      </span>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
