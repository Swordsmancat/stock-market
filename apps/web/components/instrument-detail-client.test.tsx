import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, expect, it, vi } from "vitest";

import enMessages from "../messages/en.json";
import type { InstrumentDetailPayload } from "@/lib/instrument-detail";

vi.mock("@/components/advanced-candlestick-chart", () => ({
  AdvancedCandlestickChart: () => <div data-testid="advanced-chart" />,
}));

vi.mock("@/components/intraday-price-chart", () => ({
  IntradayPriceChart: () => <div data-testid="intraday-chart" />,
}));

vi.mock("@/components/market-assistant-card", () => ({
  MarketAssistantCard: () => <div data-testid="market-assistant" />,
}));

vi.mock("@/context/market-colors-context", () => ({
  useMarketColorsContext: () => ({
    getMovementColor: () => "text-current",
  }),
}));

import { InstrumentDetailClient } from "./instrument-detail-client";

function buildDetailPayload(
  newsItems: NonNullable<InstrumentDetailPayload["news"]>["items"] = [],
  symbol = "600519",
  market = "CN",
): InstrumentDetailPayload {
  return {
    symbol,
    market,
    request_symbol: symbol,
    provider_symbol_mapped: false,
    latest: {
      status: "no_data",
      item: null,
      source: "database",
      provider: "yfinance",
      requested_provider: "yfinance",
      effective_provider: "yfinance",
    },
    bars: {
      status: "no_data",
      items: [],
      source: "database",
      provider: "yfinance",
      requested_provider: "yfinance",
      effective_provider: "yfinance",
    },
    news: {
      symbol,
      source: "database",
      summary: {
        latest_sentiment: newsItems?.[0]?.sentiment ?? null,
        article_count: newsItems?.length ?? 0,
      },
      items: newsItems,
    },
    range: {
      timeframe: "1d",
      start: "2026-01-16",
      end: "2026-07-15",
    },
  };
}

function buildDetailView({
  symbol = "600519",
  market = "CN",
  initialData,
}: {
  symbol?: string;
  market?: string;
  initialData: InstrumentDetailPayload | null;
}) {
  return (
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <InstrumentDetailClient
        symbol={symbol}
        locale="en"
        initialData={initialData}
        detailContext={{
          identity: { symbol, market, name: symbol },
          watchlistMembership: "not_watched",
        }}
      />
    </NextIntlClientProvider>
  );
}

function renderDetail(initialData: InstrumentDetailPayload | null) {
  return render(buildDetailView({ initialData }));
}

afterEach(() => {
  cleanup();
  window.sessionStorage.clear();
  vi.restoreAllMocks();
});

it("does not refresh when stored news is already available", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch");

  renderDetail(
    buildDetailPayload([
      {
        title: "Stored local news remains the initial projection",
        sentiment: "neutral",
      },
    ]),
  );

  expect(
    await screen.findByText("Stored local news remains the initial projection"),
  ).toBeInTheDocument();
  await waitFor(() => expect(fetchMock).not.toHaveBeenCalled());
});

it("does not refresh a new identity whose initial projection has stored news", async () => {
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockReturnValue(new Promise<Response>(() => undefined));
  const view = render(buildDetailView({ initialData: buildDetailPayload() }));

  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  view.rerender(
    buildDetailView({
      symbol: "000001",
      market: "CN",
      initialData: buildDetailPayload(
        [{ title: "Stored news for the next identity" }],
        "000001",
        "CN",
      ),
    }),
  );

  expect(
    await screen.findByText("Stored news for the next identity"),
  ).toBeInTheDocument();
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  expect(String(fetchMock.mock.calls[0]?.[0])).toBe(
    "/api/news/600519/refresh?market=CN",
  );
});

it("clears a previous identity news error when the new identity has stored news", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch");
  const view = render(
    buildDetailView({
      initialData: {
        ...buildDetailPayload(),
        news_load_status: "failed",
      },
    }),
  );

  expect(
    await screen.findByText("News sources are temporarily unavailable."),
  ).toBeInTheDocument();

  view.rerender(
    buildDetailView({
      symbol: "000001",
      market: "CN",
      initialData: buildDetailPayload(
        [{ title: "Stored news after the previous identity error" }],
        "000001",
        "CN",
      ),
    }),
  );

  expect(
    await screen.findByText("Stored news after the previous identity error"),
  ).toBeInTheDocument();
  expect(
    screen.queryByText("News sources are temporarily unavailable."),
  ).not.toBeInTheDocument();
  await waitFor(() => expect(fetchMock).not.toHaveBeenCalled());
});

it("resets locally rendered detail data when exact instrument identity changes", async () => {
  const firstPayload = buildDetailPayload([
    { title: "Stored news for the first identity" },
  ]);
  const secondPayload = buildDetailPayload(
    [{ title: "Stored news for the second identity" }],
    "000001",
    "CN",
  );
  const view = render(buildDetailView({ initialData: firstPayload }));

  expect(
    await screen.findByText("Stored news for the first identity"),
  ).toBeInTheDocument();

  view.rerender(
    buildDetailView({
      symbol: "000001",
      market: "CN",
      initialData: secondPayload,
    }),
  );

  expect(
    await screen.findByText("Stored news for the second identity"),
  ).toBeInTheDocument();
  expect(
    screen.queryByText("Stored news for the first identity"),
  ).not.toBeInTheDocument();
});

it("ignores a stale client detail response after identity changes", async () => {
  let resolveFirstDetail: ((response: Response) => void) | undefined;
  let resolveSecondDetail: ((response: Response) => void) | undefined;
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url === "/api/instruments/600519?market=CN") {
      return new Promise<Response>((resolve) => {
        resolveFirstDetail = resolve;
      });
    }
    if (url === "/api/instruments/000001?market=CN") {
      return new Promise<Response>((resolve) => {
        resolveSecondDetail = resolve;
      });
    }
    return Promise.reject(new Error(`Unexpected request: ${url}`));
  });
  const view = render(buildDetailView({ initialData: null }));

  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  view.rerender(
    buildDetailView({ symbol: "000001", market: "CN", initialData: null }),
  );
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));

  await act(async () => {
    resolveSecondDetail?.(
      new Response(
        JSON.stringify(
          buildDetailPayload(
            [{ title: "Current identity detail news" }],
            "000001",
            "CN",
          ),
        ),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
  });
  expect(
    await screen.findByText("Current identity detail news"),
  ).toBeInTheDocument();

  await act(async () => {
    resolveFirstDetail?.(
      new Response(
        JSON.stringify(
          buildDetailPayload([{ title: "Stale identity detail news" }]),
        ),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
  });

  await waitFor(() => {
    expect(
      screen.queryByText("Stale identity detail news"),
    ).not.toBeInTheDocument();
  });
  expect(screen.getByText("Current identity detail news")).toBeInTheDocument();
});

it("ignores a stale news refresh response after identity changes", async () => {
  let resolveFirstRefresh: ((response: Response) => void) | undefined;
  let resolveSecondRefresh: ((response: Response) => void) | undefined;
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url === "/api/news/600519/refresh?market=CN") {
      return new Promise<Response>((resolve) => {
        resolveFirstRefresh = resolve;
      });
    }
    if (url === "/api/news/000001/refresh?market=CN") {
      return new Promise<Response>((resolve) => {
        resolveSecondRefresh = resolve;
      });
    }
    return Promise.reject(new Error(`Unexpected request: ${url}`));
  });
  const view = render(buildDetailView({ initialData: buildDetailPayload() }));

  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  view.rerender(
    buildDetailView({
      symbol: "000001",
      market: "CN",
      initialData: buildDetailPayload([], "000001", "CN"),
    }),
  );
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));

  await act(async () => {
    resolveSecondRefresh?.(
      new Response(
        JSON.stringify({
          symbol: "000001",
          market: "CN",
          status: "no_data",
          diagnostics: [{ code: "DATABASE_FALLBACK_EMPTY" }],
          news: buildDetailPayload([], "000001", "CN").news,
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
  });
  expect(
    await screen.findByText(
      "No usable news was found from the available sources.",
    ),
  ).toBeInTheDocument();

  await act(async () => {
    resolveFirstRefresh?.(
      new Response(
        JSON.stringify({
          symbol: "600519",
          market: "CN",
          status: "refreshed",
          diagnostics: [{ code: "PROVIDER_PERSISTED" }],
          news: buildDetailPayload([
            { title: "Stale news from the previous identity" },
          ]).news,
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
  });

  await waitFor(() => {
    expect(
      screen.queryByText("Stale news from the previous identity"),
    ).not.toBeInTheDocument();
  });
  expect(
    screen.getByText("No usable news was found from the available sources."),
  ).toBeInTheDocument();
});

it("retries an automatic refresh after an identity-switch abort", async () => {
  const firstRequest = new Promise<Response>(() => undefined);
  const secondRequest = new Promise<Response>(() => undefined);
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockReturnValueOnce(firstRequest)
    .mockReturnValueOnce(secondRequest)
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          symbol: "600519",
          market: "CN",
          status: "refreshed",
          diagnostics: [{ code: "PROVIDER_PERSISTED" }],
          news: buildDetailPayload([
            { title: "Recovered after returning to the original identity" },
          ]).news,
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
  const view = render(buildDetailView({ initialData: buildDetailPayload() }));

  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  expect(window.sessionStorage.getItem(window.sessionStorage.key(0)!)).toBe(
    "attempted",
  );

  view.rerender(
    buildDetailView({
      symbol: "000001",
      market: "CN",
      initialData: buildDetailPayload([], "000001", "CN"),
    }),
  );
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));

  view.rerender(buildDetailView({ initialData: buildDetailPayload() }));

  expect(
    await screen.findByText(
      "Recovered after returning to the original identity",
    ),
  ).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(3);
  expect(fetchMock.mock.calls.map(([input]) => String(input))).toEqual([
    "/api/news/600519/refresh?market=CN",
    "/api/news/000001/refresh?market=CN",
    "/api/news/600519/refresh?market=CN",
  ]);
});

it("resets retry, diagnostic, and automatic-recovery state for a new identity", async () => {
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          symbol: "600519",
          market: "CN",
          status: "provider_error",
          diagnostics: [{ code: "PROVIDER_ERROR" }],
          news: buildDetailPayload().news,
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          symbol: "600519",
          market: "CN",
          status: "provider_error",
          diagnostics: [{ code: "PERSISTENCE_ERROR" }],
          news: buildDetailPayload().news,
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          symbol: "000001",
          market: "CN",
          status: "no_data",
          diagnostics: [{ code: "DATABASE_FALLBACK_EMPTY" }],
          news: buildDetailPayload([], "000001", "CN").news,
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
  const view = render(buildDetailView({ initialData: buildDetailPayload() }));

  expect(await screen.findByText("A news source failed.")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Retry news search" }));
  expect(
    await screen.findByText("Usable news could not be stored locally."),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Retry news search" }),
  ).not.toBeInTheDocument();

  view.rerender(
    buildDetailView({
      symbol: "000001",
      market: "CN",
      initialData: buildDetailPayload([], "000001", "CN"),
    }),
  );

  expect(
    await screen.findByText(
      "No usable news was found from the available sources.",
    ),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Retry news search" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByText("Usable news could not be stored locally."),
  ).not.toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(3);
});

it("does not mutate when the stored-news read itself failed", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch");
  const initialData = {
    ...buildDetailPayload(),
    news_load_status: "failed" as const,
  };

  renderDetail(initialData);

  expect(
    await screen.findByText("News sources are temporarily unavailable."),
  ).toBeInTheDocument();
  await waitFor(() => expect(fetchMock).not.toHaveBeenCalled());
});

it("shows a failed stored-news read when detail data loads on the client", async () => {
  const clientLoadedData = {
    ...buildDetailPayload(),
    news_load_status: "failed" as const,
  };
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(clientLoadedData), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );

  renderDetail(null);

  expect(
    await screen.findByText("News sources are temporarily unavailable."),
  ).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(fetchMock.mock.calls[0]?.[0]).toBe(
    "/api/instruments/600519?market=CN",
  );
});

it("recovers empty news once and replaces only the local news projection", async () => {
  const recoveredNews = {
    symbol: "600519",
    source: "database",
    summary: { latest_sentiment: "positive", article_count: 1 },
    items: [
      {
        title: "Kweichow Moutai publishes a verified company update",
        source: "provider-news",
        published_at: "2026-07-15T08:00:00Z",
        sentiment: "positive",
        confidence: 0.75,
      },
    ],
  };
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        symbol: "600519",
        market: "CN",
        status: "refreshed",
        diagnostics: [{ code: "PROVIDER_PERSISTED" }],
        news: recoveredNews,
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );

  const firstRender = renderDetail(buildDetailPayload());

  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/news/600519/refresh?market=CN",
    expect.objectContaining({ method: "POST", signal: expect.any(AbortSignal) }),
  );
  expect(
    await screen.findByText(
      "Kweichow Moutai publishes a verified company update",
    ),
  ).toBeInTheDocument();
  expect(screen.getByText("No K-line data available")).toBeInTheDocument();

  firstRender.unmount();
  renderDetail(buildDetailPayload());
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
});

it("shows a provider failure and allows exactly one explicit retry", async () => {
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          symbol: "600519",
          market: "CN",
          status: "provider_error",
          diagnostics: [
            {
              code: "PROVIDER_ERROR",
              message: "raw upstream response must stay hidden",
            },
          ],
          news: buildDetailPayload().news,
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          symbol: "600519",
          market: "CN",
          status: "refreshed",
          diagnostics: [{ code: "PROVIDER_PERSISTED" }],
          news: {
            symbol: "600519",
            source: "database",
            summary: { latest_sentiment: "neutral", article_count: 1 },
            items: [
              {
                title: "Verified news after the manual retry",
                sentiment: "neutral",
              },
            ],
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

  renderDetail(buildDetailPayload());

  expect(
    await screen.findByText("News sources are temporarily unavailable."),
  ).toBeInTheDocument();
  expect(screen.getByText("A news source failed.")).toBeInTheDocument();
  expect(
    screen.queryByText("raw upstream response must stay hidden"),
  ).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Retry news search" }));

  expect(
    await screen.findByText("Verified news after the manual retry"),
  ).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(2);
  expect(
    screen.queryByRole("button", { name: "Retry news search" }),
  ).not.toBeInTheDocument();
});

it("rejects a malformed successful refresh payload instead of showing recovered", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        symbol: "600519",
        market: "CN",
        status: "refreshed",
        diagnostics: [{ code: "PROVIDER_PERSISTED" }],
        news: {
          symbol: "600519",
          source: "database",
          items: "invalid",
        },
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );

  renderDetail(buildDetailPayload());

  expect(
    await screen.findByText("News sources are temporarily unavailable."),
  ).toBeInTheDocument();
  expect(
    screen.queryByText("News was refreshed and stored locally."),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByText("No news sentiment available."),
  ).not.toBeInTheDocument();
});

it("rejects a same-symbol refresh projection from the wrong market", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        symbol: "600519",
        market: "HK",
        status: "refreshed",
        diagnostics: [{ code: "PROVIDER_PERSISTED" }],
        news: buildDetailPayload([
          { title: "Wrong-market news must not be rendered" },
        ]).news,
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );

  renderDetail(buildDetailPayload());

  expect(
    await screen.findByText("News sources are temporarily unavailable."),
  ).toBeInTheDocument();
  expect(
    screen.queryByText("Wrong-market news must not be rendered"),
  ).not.toBeInTheDocument();
});

it("renders a localized fallback for an unknown news diagnostic code", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        symbol: "600519",
        market: "CN",
        status: "provider_error",
        diagnostics: [{ code: "NEW_PROVIDER_DIAGNOSTIC" }],
        news: buildDetailPayload().news,
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );

  renderDetail(buildDetailPayload());

  expect(
    await screen.findByText("A news source returned an unrecognized status."),
  ).toBeInTheDocument();
  expect(screen.queryByText("NEW_PROVIDER_DIAGNOSTIC")).not.toBeInTheDocument();
});

it("shows unsupported news recovery as a settings action without retrying", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        symbol: "600519",
        market: "CN",
        status: "unsupported",
        diagnostics: [{ code: "MISSING_CREDENTIALS" }],
        news: buildDetailPayload().news,
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );

  renderDetail(buildDetailPayload());

  expect(
    await screen.findByText(
      "No executable news source is configured for this instrument.",
    ),
  ).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Configure news sources" })).toHaveAttribute(
    "href",
    "/settings",
  );
  expect(
    screen.queryByRole("button", { name: "Retry news search" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByText("No news sentiment available."),
  ).not.toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it("shows visible recovery progress before a truthful no-data result", async () => {
  let resolveRefresh: ((response: Response) => void) | undefined;
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(
    () =>
      new Promise<Response>((resolve) => {
        resolveRefresh = resolve;
      }),
  );

  renderDetail(buildDetailPayload());

  expect(
    await screen.findByText("Checking configured news sources once..."),
  ).toBeInTheDocument();
  expect(
    screen.queryByText("No news sentiment available."),
  ).not.toBeInTheDocument();
  resolveRefresh?.(
    new Response(
      JSON.stringify({
        symbol: "600519",
        market: "CN",
        status: "no_data",
        diagnostics: [{ code: "DATABASE_FALLBACK_EMPTY" }],
        news: buildDetailPayload().news,
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );

  expect(
    await screen.findByText(
      "No usable news was found from the available sources.",
    ),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Retry news search" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByText("No news sentiment available."),
  ).not.toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(String(fetchMock.mock.calls[0]?.[0])).not.toContain("assistant");
  expect(String(fetchMock.mock.calls[0]?.[0])).not.toContain("reports");
});

it("restores a no-data terminal session with one manual retry available", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        symbol: "600519",
        market: "CN",
        status: "no_data",
        diagnostics: [{ code: "DATABASE_FALLBACK_EMPTY" }],
        news: buildDetailPayload().news,
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );
  const firstView = renderDetail(buildDetailPayload());

  expect(
    await screen.findByText(
      "No usable news was found from the available sources.",
    ),
  ).toBeInTheDocument();
  expect(window.sessionStorage.length).toBe(1);
  expect(window.sessionStorage.getItem(window.sessionStorage.key(0)!)).toBe(
    "no_data",
  );

  firstView.unmount();
  renderDetail(buildDetailPayload());

  expect(
    await screen.findByText(
      "No usable news was found from the available sources.",
    ),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Retry news search" }),
  ).toBeInTheDocument();
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
});

it("treats a pre-existing attempted marker as interrupted with manual retry", async () => {
  const now = new Date();
  const localDate = [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
  ].join("-");
  window.sessionStorage.setItem(
    `news-fallback:v1:CN:600519:${localDate}`,
    "attempted",
  );
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        symbol: "600519",
        market: "CN",
        status: "no_data",
        diagnostics: [{ code: "DATABASE_FALLBACK_EMPTY" }],
        news: buildDetailPayload().news,
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );

  renderDetail(buildDetailPayload());

  expect(
    await screen.findByText("News sources are temporarily unavailable."),
  ).toBeInTheDocument();
  expect(fetchMock).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: "Retry news search" }));

  expect(
    await screen.findByText(
      "No usable news was found from the available sources.",
    ),
  ).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it("restores a provider-error terminal session with one manual retry available", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        symbol: "600519",
        market: "CN",
        status: "provider_error",
        diagnostics: [{ code: "PERSISTENCE_ERROR" }],
        news: buildDetailPayload().news,
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );
  const firstView = renderDetail(buildDetailPayload());

  expect(
    await screen.findByText("News sources are temporarily unavailable."),
  ).toBeInTheDocument();
  expect(
    screen.getByText("Usable news could not be stored locally."),
  ).toBeInTheDocument();
  expect(window.sessionStorage.getItem(window.sessionStorage.key(0)!)).toBe(
    "provider_error",
  );

  firstView.unmount();
  renderDetail(buildDetailPayload());

  expect(
    await screen.findByText("News sources are temporarily unavailable."),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Retry news search" }),
  ).toBeInTheDocument();
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
});

it("restores an unsupported terminal session with settings and no retry", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        symbol: "600519",
        market: "CN",
        status: "unsupported",
        diagnostics: [{ code: "UNSUPPORTED_IDENTITY" }],
        news: buildDetailPayload().news,
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );
  const firstView = renderDetail(buildDetailPayload());

  expect(
    await screen.findByText(
      "No executable news source is configured for this instrument.",
    ),
  ).toBeInTheDocument();
  expect(
    screen.getByText(
      "The instrument identity is not supported by the available news sources.",
    ),
  ).toBeInTheDocument();
  expect(window.sessionStorage.getItem(window.sessionStorage.key(0)!)).toBe(
    "unsupported",
  );

  firstView.unmount();
  renderDetail(buildDetailPayload());

  expect(
    await screen.findByText(
      "No executable news source is configured for this instrument.",
    ),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Configure news sources" }),
  ).toHaveAttribute("href", "/settings");
  expect(
    screen.queryByRole("button", { name: "Retry news search" }),
  ).not.toBeInTheDocument();
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
});
