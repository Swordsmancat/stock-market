import { backendFetch } from "@/lib/backend-api";

type MarketDailyDataStatus = "ok" | "degraded" | "unavailable";
type MarketDailyDataMode = "live" | "delayed" | "mock" | "none";

function unavailableMarketDailyDataPayload(message: string) {
  return {
    status: "unavailable" satisfies MarketDailyDataStatus,
    data_mode: "none" satisfies MarketDailyDataMode,
    source: "backend_proxy",
    message,
    count: 0,
    items: [],
  };
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const backendSearchParams = new URLSearchParams({
    market: normalizeMarket(searchParams.get("market")),
    limit: String(normalizeLimit(searchParams.get("limit"), 50)),
  });
  const tradeDate = searchParams.get("date")?.trim();
  if (tradeDate) {
    backendSearchParams.set("date", tradeDate);
  }
  const provider = searchParams.get("provider")?.trim();
  if (provider) {
    backendSearchParams.set("provider", provider);
  }

  try {
    const response = await backendFetch(
      `/market-daily-data/dragon-tiger-list?${backendSearchParams.toString()}`,
      { cache: "no-store" },
    );

    if (!response.ok) {
      return Response.json(
        unavailableMarketDailyDataPayload("Failed to fetch Dragon Tiger List data"),
        { status: 502 },
      );
    }

    const data = await response.json();
    return Response.json(data);
  } catch (error) {
    console.error("Dragon Tiger List API error:", error);
    return Response.json(unavailableMarketDailyDataPayload("Internal server error"), {
      status: 502,
    });
  }
}

function normalizeLimit(rawLimit: string | null, defaultLimit: number): number {
  const parsedLimit = Number.parseInt(rawLimit ?? String(defaultLimit), 10);
  if (Number.isNaN(parsedLimit)) {
    return defaultLimit;
  }
  return Math.min(Math.max(parsedLimit, 1), 100);
}

function normalizeMarket(rawMarket: string | null): string {
  const market = rawMarket?.trim().toUpperCase();
  return market || "CN";
}
