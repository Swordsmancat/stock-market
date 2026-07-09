"use client";

import * as React from "react";
import { AlertTriangle, FileText, ShieldCheck, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";

import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import {
  FinancialTerminalCard,
  FinancialTerminalCardContent,
  FinancialTerminalCardHeader,
  FinancialTerminalSurface,
} from "@/components/financial-terminal-section";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardDescription, CardTitle } from "@/components/ui/card";

export type ResearchBriefCitation = {
  id: string;
  label?: string | null;
  source?: string | null;
  source_type?: string | null;
  as_of?: string | null;
};

export type ResearchBriefPayload = {
  id: string;
  title: string;
  brief_type: string;
  scope?: Record<string, unknown>;
  content_markdown: string;
  citations?: ResearchBriefCitation[];
  source_summary?: {
    source_gap_count?: number;
    source_mix?: Record<string, number>;
  };
  diagnostics?: Array<{
    code?: string | null;
    message?: string | null;
    severity?: string | null;
  }>;
  model?: {
    provider?: string | null;
    name?: string | null;
    used_llm?: boolean;
    fallback_reason?: string | null;
  };
  safety?: {
    not_investment_advice?: boolean;
    no_buy_sell_hold?: boolean;
    no_automated_trading?: boolean;
    no_fabricated_macro_data?: boolean;
  };
  created_at: string;
};

export type ResearchBriefInboxLabels = {
  title: string;
  description: string;
  generateAction: string;
  generating: string;
  generateSuccess: string;
  generateFailed: string;
  loadFailedTitle: string;
  loadFailedDescription: string;
  emptyTitle: string;
  emptyDescription: string;
  createdAt: string;
  modelGenerated: string;
  modelFallback: string;
  modelName: string;
  citationsCount: string;
  sourceGapsCount: string;
  diagnosticsCount: string;
  contentTitle: string;
  safetyTitle: string;
  safetyNotAdvice: string;
  safetyNoTrading: string;
  safetyNoFabricatedData: string;
  unavailableShort: string;
};

type ResearchBriefInboxProps = {
  labels: ResearchBriefInboxLabels;
  initialBriefs: ResearchBriefPayload[];
  loadFailed?: boolean;
  provider: string;
  locale: string;
};

function formatLabel(
  template: string,
  values: Record<string, string | number>,
): string {
  return Object.entries(values).reduce(
    (message, [key, value]) => message.replace(`{${key}}`, String(value)),
    template,
  );
}

function formatDate(
  value: string,
  locale: string,
  unavailableLabel: string,
): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return unavailableLabel;
  }
  return parsed.toLocaleString(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function briefMetric(label: string, value: number) {
  return (
    <FinancialTerminalSurface className="p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 font-mono text-xl font-semibold">{value}</div>
    </FinancialTerminalSurface>
  );
}

function modelLabel(
  brief: ResearchBriefPayload,
  labels: ResearchBriefInboxLabels,
): string {
  return brief.model?.used_llm ? labels.modelGenerated : labels.modelFallback;
}

function diagnosticLabel(diagnostic: {
  code?: string | null;
  message?: string | null;
  severity?: string | null;
}) {
  return (
    [diagnostic.severity, diagnostic.code].filter(Boolean).join("/") ||
    diagnostic.message ||
    "diagnostic"
  );
}

export function ResearchBriefInbox({
  labels,
  initialBriefs,
  loadFailed = false,
  provider,
  locale,
}: ResearchBriefInboxProps) {
  const [briefs, setBriefs] =
    React.useState<ResearchBriefPayload[]>(initialBriefs);
  const [isGenerating, setIsGenerating] = React.useState(false);
  const [message, setMessage] = React.useState<string | null>(null);
  const router = useRouter();

  async function handleGenerate() {
    setIsGenerating(true);
    setMessage(null);
    try {
      const response = await fetch("/api/research-briefs", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          provider,
          locale: locale.startsWith("zh") ? "zh" : "en",
        }),
      });
      const payload = (await response.json()) as ResearchBriefPayload;
      if (!response.ok) {
        throw new Error(labels.generateFailed);
      }
      setBriefs((current) => [
        payload,
        ...current.filter((item) => item.id !== payload.id),
      ]);
      setMessage(labels.generateSuccess);
      router.refresh();
    } catch {
      setMessage(labels.generateFailed);
    } finally {
      setIsGenerating(false);
    }
  }

  return (
    <FinancialTerminalCard>
      <FinancialTerminalCardHeader>
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-xl">
              <FileText className="h-5 w-5" />
              {labels.title}
            </CardTitle>
            <CardDescription className="mt-1">
              {labels.description}
            </CardDescription>
          </div>
          <Button onClick={handleGenerate} disabled={isGenerating}>
            <Sparkles
              className={`mr-2 h-4 w-4 ${isGenerating ? "animate-pulse" : ""}`}
            />
            {isGenerating ? labels.generating : labels.generateAction}
          </Button>
        </div>
      </FinancialTerminalCardHeader>
      <FinancialTerminalCardContent className="space-y-4">
        {message ? (
          <p className="text-sm text-muted-foreground">{message}</p>
        ) : null}
        {loadFailed ? (
          <ErrorState
            title={labels.loadFailedTitle}
            description={labels.loadFailedDescription}
          />
        ) : null}
        {!loadFailed && briefs.length === 0 ? (
          <EmptyState
            title={labels.emptyTitle}
            description={labels.emptyDescription}
          />
        ) : null}
        {!loadFailed && briefs.length > 0 ? (
          <div className="grid gap-4 xl:grid-cols-2">
            {briefs.map((brief) => {
              const citationCount = brief.citations?.length ?? 0;
              const sourceGapCount =
                brief.source_summary?.source_gap_count ?? 0;
              const diagnosticCount = brief.diagnostics?.length ?? 0;
              return (
                <FinancialTerminalSurface key={brief.id} className="p-4">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge
                          variant={
                            brief.model?.used_llm ? "secondary" : "outline"
                          }
                        >
                          {modelLabel(brief, labels)}
                        </Badge>
                        {brief.model?.name ? (
                          <Badge variant="outline">
                            {formatLabel(labels.modelName, {
                              name: brief.model.name,
                            })}
                          </Badge>
                        ) : null}
                      </div>
                      <h3 className="mt-2 font-semibold">{brief.title}</h3>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {formatLabel(labels.createdAt, {
                          date: formatDate(
                            brief.created_at,
                            locale,
                            labels.unavailableShort,
                          ),
                        })}
                      </p>
                    </div>
                    <div className="font-mono text-xs text-muted-foreground">
                      {brief.id}
                    </div>
                  </div>

                  <div className="mt-4 grid gap-2 sm:grid-cols-3">
                    {briefMetric(labels.citationsCount, citationCount)}
                    {briefMetric(labels.sourceGapsCount, sourceGapCount)}
                    {briefMetric(labels.diagnosticsCount, diagnosticCount)}
                  </div>

                  <div className="mt-4">
                    <div className="text-sm font-semibold">
                      {labels.contentTitle}
                    </div>
                    <FinancialTerminalSurface className="mt-2 max-h-72 overflow-auto bg-muted/20 p-3 text-sm leading-6 whitespace-pre-wrap">
                      {brief.content_markdown}
                    </FinancialTerminalSurface>
                  </div>

                  {(brief.diagnostics ?? []).length > 0 ? (
                    <FinancialTerminalSurface className="mt-4 border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-200">
                      <div className="flex items-center gap-2 font-semibold">
                        <AlertTriangle className="h-4 w-4" />
                        {labels.diagnosticsCount}
                      </div>
                      <ul className="mt-2 list-disc space-y-1 pl-4">
                        {brief.diagnostics
                          ?.slice(0, 4)
                          .map((diagnostic, index) => (
                            <li
                              key={`${brief.id}-diagnostic-${diagnostic.code ?? index}`}
                            >
                              {diagnosticLabel(diagnostic)}
                            </li>
                          ))}
                      </ul>
                    </FinancialTerminalSurface>
                  ) : null}

                  {brief.safety ? (
                    <div className="mt-4 space-y-2 text-sm">
                      <div className="flex items-center gap-2 font-semibold">
                        <ShieldCheck className="h-4 w-4" />
                        {labels.safetyTitle}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {brief.safety.not_investment_advice ? (
                          <Badge variant="secondary">
                            {labels.safetyNotAdvice}
                          </Badge>
                        ) : null}
                        {brief.safety.no_buy_sell_hold ||
                        brief.safety.no_automated_trading ? (
                          <Badge variant="secondary">
                            {labels.safetyNoTrading}
                          </Badge>
                        ) : null}
                        {brief.safety.no_fabricated_macro_data ? (
                          <Badge variant="secondary">
                            {labels.safetyNoFabricatedData}
                          </Badge>
                        ) : null}
                      </div>
                    </div>
                  ) : null}
                </FinancialTerminalSurface>
              );
            })}
          </div>
        ) : null}
      </FinancialTerminalCardContent>
    </FinancialTerminalCard>
  );
}
