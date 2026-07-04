export type MarketAssistantStatus = "ok" | "degraded" | "no_data" | "error";

export type MarketAssistantRequest = {
  scope?: "instrument";
  symbol: string;
  question: string;
  locale?: "zh" | "en";
  timeframe?: "1d";
  start?: string | null;
  end?: string | null;
  provider?: string | null;
};

export type MarketAssistantCitation = {
  id: string;
  label: string;
  source: string;
  url?: string | null;
};

export type MarketAssistantDiagnostic = {
  source: string;
  status: string;
  message: string;
};

export type MarketAssistantResponse = {
  status: MarketAssistantStatus;
  answer_markdown: string;
  symbol: string;
  as_of?: string | null;
  model: {
    provider: string;
    name: string;
    used_llm: boolean;
    fallback_reason?: string | null;
  };
  context: {
    scope?: string;
    timeframe: string;
    start: string;
    end: string;
    latest_close?: number | null;
    period_change_pct?: number | null;
    bar_count: number;
    price_summary?: string;
    indicator_summary?: string;
    fundamental_summary?: string;
    news_summary?: string;
    source?: string | null;
    provider?: string | null;
    requested_provider?: string | null;
    effective_provider?: string | null;
  };
  citations: MarketAssistantCitation[];
  diagnostics: MarketAssistantDiagnostic[];
  safety: {
    not_investment_advice: boolean;
    no_fabricated_market_data: boolean;
    disclaimer: string;
  };
};


export async function askMarketAssistant(request: MarketAssistantRequest): Promise<MarketAssistantResponse> {
  const response = await fetch("/api/assistant/market", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      scope: request.scope ?? "instrument",
      symbol: request.symbol,
      question: request.question,
      locale: request.locale ?? "zh",
      timeframe: request.timeframe ?? "1d",
      start: request.start ?? undefined,
      end: request.end ?? undefined,
      provider: request.provider ?? undefined,
    }),
  });

  const responseBody = await response.text();
  const parsedBody = responseBody ? JSON.parse(responseBody) : null;
  if (!response.ok) {
    const reason = extractErrorReason(parsedBody, response.status);
    throw new Error(reason);
  }

  return parsedBody as MarketAssistantResponse;
}


function extractErrorReason(parsedBody: unknown, responseStatus: number): string {
  if (typeof parsedBody === "object" && parsedBody !== null && "detail" in parsedBody) {
    const detail = (parsedBody as { detail?: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (typeof detail === "object" && detail !== null && "message" in detail) {
      const message = (detail as { message?: unknown }).message;
      if (typeof message === "string") {
        return message;
      }
    }
  }

  return `Assistant request failed with status ${responseStatus}`;
}
