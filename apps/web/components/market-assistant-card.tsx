"use client";

import { FormEvent, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { askMarketAssistant } from "@/lib/market-assistant";
import type { MarketAssistantResponse, MarketAssistantStatus } from "@/lib/market-assistant";

type MarketAssistantCardProps = {
  symbol: string;
  locale: string;
  provider?: string | null;
  start?: string | null;
  end?: string | null;
};

const QUICK_PROMPT_IDS = ["trend", "risk", "data"] as const;

export function MarketAssistantCard({
  symbol,
  locale,
  provider = null,
  start = null,
  end = null,
}: MarketAssistantCardProps) {
  const t = useTranslations("MarketAssistant");
  const normalizedLocale = locale === "en" ? "en" : "zh";
  const defaultQuestion = useMemo(() => t("defaultQuestion", { symbol }), [symbol, t]);
  const [question, setQuestion] = useState(defaultQuestion);
  const [response, setResponse] = useState<MarketAssistantResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submitQuestion(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      const assistantResponse = await askMarketAssistant({
        scope: "instrument",
        symbol,
        question: trimmedQuestion,
        locale: normalizedLocale,
        timeframe: "1d",
        start,
        end,
        provider,
      });
      setResponse(assistantResponse);
    } catch (caughtError) {
      setResponse(null);
      setError(caughtError instanceof Error ? caughtError.message : t("unknownError"));
    } finally {
      setIsSubmitting(false);
    }
  }

  function applyQuickPrompt(promptId: (typeof QUICK_PROMPT_IDS)[number]) {
    setQuestion(t(`quickPrompt${promptId}` as never, { symbol } as never));
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle>{t("title")}</CardTitle>
            <CardDescription>{t("description")}</CardDescription>
          </div>
          {response ? <AssistantStatusBadge status={response.status} /> : null}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <form className="space-y-3" onSubmit={submitQuestion}>
          <label className="text-sm font-medium" htmlFor="market-assistant-question">
            {t("questionLabel")}
          </label>
          <textarea
            id="market-assistant-question"
            className="min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm outline-none transition-colors placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder={t("questionPlaceholder")}
            disabled={isSubmitting}
          />
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="flex flex-wrap gap-2">
              {QUICK_PROMPT_IDS.map((promptId) => (
                <Button
                  key={promptId}
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => applyQuickPrompt(promptId)}
                  disabled={isSubmitting}
                >
                  {t(`quickPrompt${promptId}Label` as never)}
                </Button>
              ))}
            </div>
            <Button type="submit" disabled={isSubmitting || !question.trim()}>
              {isSubmitting ? t("submitting") : t("submit")}
            </Button>
          </div>
        </form>

        {error ? (
          <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
            {t("errorPrefix", { reason: error })}
          </div>
        ) : null}

        {response ? <AssistantResponsePanel response={response} /> : <InitialEmptyState />}
      </CardContent>
    </Card>
  );
}

function AssistantStatusBadge({ status }: { status: MarketAssistantStatus }) {
  const t = useTranslations("MarketAssistant");
  const variant = status === "ok" ? "default" : "secondary";
  return <Badge variant={variant}>{t(`status${status}` as never)}</Badge>;
}

function AssistantResponsePanel({ response }: { response: MarketAssistantResponse }) {
  const t = useTranslations("MarketAssistant");
  return (
    <div className="space-y-4 rounded-md border bg-muted/30 p-4">
      <div className="space-y-2">
        <div className="text-sm font-semibold">{t("answerTitle")}</div>
        <div className="whitespace-pre-wrap text-sm leading-6">{response.answer_markdown}</div>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <Metric label={t("barCount")} value={String(response.context.bar_count)} />
        <Metric label={t("latestClose")} value={formatNullableNumber(response.context.latest_close)} />
        <Metric label={t("periodChange")} value={formatPercent(response.context.period_change_pct)} />
      </div>

      {response.citations.length > 0 ? (
        <div className="space-y-2">
          <div className="text-sm font-semibold">{t("citationsTitle")}</div>
          <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
            {response.citations.map((citation) => (
              <li key={citation.id}>
                {citation.label} <span className="font-mono">({citation.source})</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {response.diagnostics.length > 0 ? (
        <div className="space-y-2">
          <div className="text-sm font-semibold">{t("diagnosticsTitle")}</div>
          <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
            {response.diagnostics.map((diagnostic) => (
              <li key={`${diagnostic.source}:${diagnostic.status}:${diagnostic.message}`}>
                {diagnostic.source}: {diagnostic.message}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="rounded-md border bg-background p-3 text-xs text-muted-foreground">
        {response.safety.disclaimer}
      </div>
    </div>
  );
}

function InitialEmptyState() {
  const t = useTranslations("MarketAssistant");
  return <p className="text-sm text-muted-foreground">{t("emptyState")}</p>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-background p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-sm font-semibold">{value}</div>
    </div>
  );
}

function formatNullableNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "--";
  }
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "--";
  }
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}%`;
}
