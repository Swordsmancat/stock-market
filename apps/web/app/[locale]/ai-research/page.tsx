import {
  AiResearchDesk,
  type AiResearchBlockTradeItem,
  type AiResearchDiagnostic,
  type AiResearchDragonTigerItem,
  type AiResearchFollowedItem,
  type AiResearchLimitUpReasonItem,
  type AiResearchMacroIndicator,
  type AiResearchMarketDailyDataPayload,
  type AiResearchOfficialSourceStatus,
  type AiResearchRecommendation,
  type AiResearchStockFundFlowItem,
  type AiResearchWatchlistItem,
} from "@/components/ai-research-desk";
import {
  StockDiscoveryPanel,
  type StockSelectionProfilesPayload,
  type StockUniverseStatusPayload,
} from "@/components/stock-discovery-panel";
import {
  AshareEvidenceCoveragePanel,
  type EvidenceCoveragePayload,
} from "@/components/ashare-evidence-coverage-panel";
import { DailyResearchShortlistPanel } from "@/components/daily-research-shortlist-panel";
import { backendFetch } from "@/lib/backend-api";
import type { DailyResearchShortlistPayload } from "@/lib/daily-research-shortlist";
import { withProviderQuery } from "@/lib/market-data";
import { getPlatformSettings } from "@/lib/platform-settings-store";

type WatchlistPayload = {
  items?: AiResearchWatchlistItem[];
};

type MarketOverviewPayload = {
  generated_at?: string | null;
  provider?: string | null;
  followed?: {
    items?: AiResearchFollowedItem[];
  };
  macro_indicators?: {
    items?: AiResearchMacroIndicator[];
  };
  valuation_indicators?: {
    items?: AiResearchMacroIndicator[];
  };
  dashboard_brief?: {
    diagnostics?: AiResearchDiagnostic[];
  } | null;
  diagnostics?: AiResearchDiagnostic[];
};

type RecommendationsPayload = {
  status?: string | null;
  diagnostics?: AiResearchDiagnostic[];
  items?: AiResearchRecommendation[];
};

type OfficialSourceStatusPayload = AiResearchOfficialSourceStatus;
type StockFundFlowPayload = AiResearchMarketDailyDataPayload<AiResearchStockFundFlowItem>;
type LimitUpReasonsPayload = AiResearchMarketDailyDataPayload<AiResearchLimitUpReasonItem>;
type DragonTigerPayload = AiResearchMarketDailyDataPayload<AiResearchDragonTigerItem>;
type BlockTradesPayload = AiResearchMarketDailyDataPayload<AiResearchBlockTradeItem>;

type OptionalLoadResult<T> =
  | { status: "loaded"; payload: T }
  | { status: "failed" };

const RECOMMENDATION_SYMBOL_LIMIT = 8;
const RECOMMENDATION_ITEM_LIMIT = 6;

export default async function AiResearchPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const settings = await getPlatformSettings();
  const provider = settings.market_data_provider;

  const [
    watchlistResult,
    marketOverviewResult,
    officialSourceStatusResult,
    stockFundFlowResult,
    limitUpReasonsResult,
    dragonTigerResult,
    blockTradesResult,
    stockSelectionProfilesResult,
    stockUniverseStatusResult,
    evidenceCoverageResult,
    dailyShortlistResult,
  ] = await Promise.all([
    fetchOptionalJson<WatchlistPayload>("/watchlist"),
    fetchOptionalJson<MarketOverviewPayload>(withProviderQuery("/dashboard/market-overview", provider)),
    fetchOptionalJson<OfficialSourceStatusPayload>("/market-indicators/official-sources/status"),
    fetchOptionalJson<StockFundFlowPayload>(
      "/market-daily-data/fund-flow/stocks?market=CN&window=today&limit=6&provider=akshare",
    ),
    fetchOptionalJson<LimitUpReasonsPayload>(
      "/market-daily-data/limit-up-reasons?market=CN&limit=6&provider=akshare",
    ),
    fetchOptionalJson<DragonTigerPayload>(
      "/market-daily-data/dragon-tiger-list?market=CN&limit=6&provider=akshare",
    ),
    fetchOptionalJson<BlockTradesPayload>(
      "/market-daily-data/block-trades?market=CN&limit=6&provider=akshare",
    ),
    fetchOptionalJson<StockSelectionProfilesPayload>("/stock-selection/profiles"),
    fetchOptionalJson<StockUniverseStatusPayload>("/stock-selection/universe-status"),
    fetchOptionalJson<EvidenceCoveragePayload>(
      "/stock-selection/evidence-coverage?market=CN&provider=akshare",
    ),
    fetchOptionalJson<DailyResearchShortlistPayload>(
      "/research-shortlists/latest?market=CN&profile_id=balanced_research",
    ),
  ]);

  const watchlistItems = watchlistResult.status === "loaded" ? watchlistResult.payload.items ?? [] : [];
  const marketOverviewPayload = marketOverviewResult.status === "loaded" ? marketOverviewResult.payload : null;
  const followedItems = marketOverviewPayload?.followed?.items ?? [];
  const recommendationSymbols = buildRecommendationSymbols(watchlistItems, followedItems);
  const recommendationsResult =
    recommendationSymbols.length > 0
      ? await fetchOptionalJson<RecommendationsPayload>(
          `/recommendations?symbols=${encodeURIComponent(recommendationSymbols.join(","))}&limit=${RECOMMENDATION_ITEM_LIMIT}`,
        )
      : { status: "failed" as const };

  const recommendationsPayload = recommendationsResult.status === "loaded" ? recommendationsResult.payload : null;

  return (
    <div className="space-y-6">
      <DailyResearchShortlistPanel
        locale={locale}
        initialPayload={
          dailyShortlistResult.status === "loaded" ? dailyShortlistResult.payload : null
        }
        initialLoadFailed={dailyShortlistResult.status === "failed"}
      />
      <AiResearchDesk
        locale={locale}
        provider={marketOverviewPayload?.provider ?? provider}
        generatedAt={marketOverviewPayload?.generated_at ?? null}
        watchlistItems={watchlistItems}
        followedItems={followedItems}
        recommendations={recommendationsPayload?.items ?? []}
        recommendationStatus={recommendationsPayload?.status ?? null}
        recommendationDiagnostics={recommendationsPayload?.diagnostics ?? []}
        macroIndicators={getMacroIndicators(marketOverviewPayload)}
        officialSourceStatus={
          officialSourceStatusResult.status === "loaded" ? officialSourceStatusResult.payload : null
        }
        stockFundFlowPayload={
          stockFundFlowResult.status === "loaded" ? stockFundFlowResult.payload : null
        }
        limitUpReasonsPayload={
          limitUpReasonsResult.status === "loaded" ? limitUpReasonsResult.payload : null
        }
        dragonTigerPayload={
          dragonTigerResult.status === "loaded" ? dragonTigerResult.payload : null
        }
        blockTradesPayload={
          blockTradesResult.status === "loaded" ? blockTradesResult.payload : null
        }
        overviewDiagnostics={[
          ...(marketOverviewResult.status === "failed"
            ? [
                {
                  source: "market_overview",
                  status: "unavailable",
                  severity: "warning",
                  code: "MARKET_OVERVIEW_UNAVAILABLE",
                  message: null,
                },
              ]
            : []),
          ...(marketOverviewPayload?.dashboard_brief?.diagnostics ?? []),
          ...(marketOverviewPayload?.diagnostics ?? []),
        ]}
      />
      <AshareEvidenceCoveragePanel
        initialCoverage={
          evidenceCoverageResult.status === "loaded" ? evidenceCoverageResult.payload : null
        }
      />
      <StockDiscoveryPanel
        initialProfiles={
          stockSelectionProfilesResult.status === "loaded"
            ? stockSelectionProfilesResult.payload
            : null
        }
        initialUniverseStatus={
          stockUniverseStatusResult.status === "loaded"
            ? stockUniverseStatusResult.payload
            : null
        }
      />
    </div>
  );
}

async function fetchOptionalJson<T>(path: string): Promise<OptionalLoadResult<T>> {
  try {
    const response = await backendFetch(path, { cache: "no-store" });
    if (!response.ok) {
      return { status: "failed" };
    }
    return { status: "loaded", payload: (await response.json()) as T };
  } catch {
    return { status: "failed" };
  }
}

function buildRecommendationSymbols(
  watchlistItems: AiResearchWatchlistItem[],
  followedItems: AiResearchFollowedItem[],
): string[] {
  const symbols = new Set<string>();
  for (const item of [...watchlistItems, ...followedItems]) {
    const symbol = item.symbol?.trim().toUpperCase();
    if (symbol) {
      symbols.add(symbol);
    }
    if (symbols.size >= RECOMMENDATION_SYMBOL_LIMIT) {
      break;
    }
  }
  return [...symbols];
}

function getMacroIndicators(payload: MarketOverviewPayload | null): AiResearchMacroIndicator[] {
  const indicatorsByCode = new Map<string, AiResearchMacroIndicator>();
  for (const indicator of [
    ...(payload?.macro_indicators?.items ?? []),
    ...(payload?.valuation_indicators?.items ?? []),
  ]) {
    indicatorsByCode.set(indicator.code, indicator);
  }
  return [...indicatorsByCode.values()];
}
