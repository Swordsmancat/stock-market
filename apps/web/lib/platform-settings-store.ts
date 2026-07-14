import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";

import {
  OPENAI_API_BASE,
  OPENAI_MODEL,
  isValidLlmApiBase,
  normalizeLlmApiBase,
  normalizeLlmModel,
} from "@/lib/llm-api-presets";

/** Shared with Python backend at repo/data/platform_settings.json */

export type ColorScheme = "china" | "international";

export const HOME_INDEX_DISPLAY_FIELD_VALUES = [
  "latest_close",
  "percent_change",
  "freshness",
  "as_of",
  "region",
  "provider",
] as const;

export type HomeIndexDisplayField =
  (typeof HOME_INDEX_DISPLAY_FIELD_VALUES)[number];

export const DEFAULT_FAVORITE_HOME_INDEX_CODES = [
  "us_sp_500",
  "us_nasdaq_composite",
  "us_dow_jones",
  "cn_shanghai_composite",
  "cn_shenzhen_component",
  "cn_csi_300",
  "cn_chinext",
  "cn_csi_500",
] as const;

export const DEFAULT_HOME_INDEX_DISPLAY_FIELDS = [
  "latest_close",
  "percent_change",
  "freshness",
  "as_of",
  "region",
] as const satisfies readonly HomeIndexDisplayField[];

export const DEFAULT_FAVORITE_MACRO_INDICATOR_CODES = [
  "buffett_indicator_us",
  "buffett_indicator_cn",
  "buffett_indicator_hk",
  "us_10y_yield",
  "us_10y_2y_spread",
  "us_cpi_yoy",
  "us_m2_yoy",
  "cn_m2_yoy",
] as const;

export const NEWS_SEARCH_PROVIDER_IDS = [
  "anspire",
  "serpapi_baidu",
  "tavily",
  "bocha",
  "brave",
  "minimax",
  "yfinance",
  "akshare",
  "tushare",
  "mock",
] as const;

export const DEFAULT_NEWS_SEARCH_PROVIDER_ORDER = [
  ...NEWS_SEARCH_PROVIDER_IDS,
] as const;
export const DEFAULT_NEWS_SEARCH_ENABLED_PROVIDERS = [
  "anspire",
  "serpapi_baidu",
] as const;

export type NewsSearchProviderId = (typeof NEWS_SEARCH_PROVIDER_IDS)[number];

export type PlatformSettings = {
  market_data_provider: string;
  llm_provider: string;
  llm_api_key: string;
  llm_api_base: string;
  llm_model: string;
  akshare_enabled: boolean;
  tushare_token: string;
  tushare_http_url: string;
  color_scheme: ColorScheme;
  favorite_home_index_codes: string[];
  home_index_display_fields: HomeIndexDisplayField[];
  favorite_macro_indicator_codes: string[];
  news_search_provider_order: NewsSearchProviderId[];
  news_search_enabled_providers: NewsSearchProviderId[];
  news_search_provider_keys: Record<string, string>;
  news_search_max_results: number;
  news_search_timeout_seconds: number;
  llm_api_key_configured: boolean;
  tushare_token_configured: boolean;
  news_search_provider_keys_configured: Record<string, boolean>;
  market_data_provider_capabilities: MarketDataProviderCapability[];
  news_search_provider_capabilities: NewsSearchProviderCapability[];
};

export type MarketDataProviderCapability = {
  provider: string;
  active: boolean;
  configured: boolean;
  category: string;
  supports_daily_bars: boolean;
  supports_realtime_quotes: boolean;
  readiness_note: string;
};

export type NewsSearchProviderCapability = {
  provider: NewsSearchProviderId;
  display_name: string;
  enabled: boolean;
  configured: boolean;
  credential_required: boolean;
  credential_configured: boolean;
  credential_field: string | null;
  priority: number;
  supported_markets: string[];
  supported_regions: string[];
  supported_result_kinds: string[];
  default_timeout_seconds: number;
  default_max_results: number;
  implementation_status: string;
  readiness_note: string;
  citation_caveat: string;
};

type StoredPlatformSettings = Omit<
  PlatformSettings,
  | "llm_api_key_configured"
  | "tushare_token_configured"
  | "news_search_provider_keys_configured"
  | "market_data_provider_capabilities"
  | "news_search_provider_capabilities"
>;

const configuredDefaultLlmApiBase = normalizeLlmApiBase(
  process.env.LLM_API_BASE ?? "",
);
const hasInvalidConfiguredDefaultLlmApiBase = Boolean(
  configuredDefaultLlmApiBase &&
    !isValidLlmApiBase(configuredDefaultLlmApiBase),
);
const DEFAULT_LLM_API_BASE = isValidLlmApiBase(configuredDefaultLlmApiBase)
  ? configuredDefaultLlmApiBase
  : OPENAI_API_BASE;
const DEFAULT_LLM_MODEL =
  normalizeLlmModel(process.env.LLM_MODEL) || OPENAI_MODEL;
const DEFAULT_LLM_PROVIDER =
  process.env.LLM_PROVIDER?.trim().toLowerCase() === "openai"
    ? "openai"
    : "mock";

const DEFAULTS: StoredPlatformSettings = {
  market_data_provider:
    process.env.NEXT_PUBLIC_MARKET_DATA_PROVIDER ?? "yfinance",
  llm_provider: hasInvalidConfiguredDefaultLlmApiBase
    ? "mock"
    : DEFAULT_LLM_PROVIDER,
  llm_api_key: hasInvalidConfiguredDefaultLlmApiBase
    ? ""
    : (process.env.LLM_API_KEY ?? ""),
  llm_api_base: DEFAULT_LLM_API_BASE,
  llm_model: DEFAULT_LLM_MODEL,
  akshare_enabled: false,
  tushare_token: "",
  tushare_http_url: "",
  color_scheme: "china",
  favorite_home_index_codes: [...DEFAULT_FAVORITE_HOME_INDEX_CODES],
  home_index_display_fields: [...DEFAULT_HOME_INDEX_DISPLAY_FIELDS],
  favorite_macro_indicator_codes: [...DEFAULT_FAVORITE_MACRO_INDICATOR_CODES],
  news_search_provider_order: [...DEFAULT_NEWS_SEARCH_PROVIDER_ORDER],
  news_search_enabled_providers: [...DEFAULT_NEWS_SEARCH_ENABLED_PROVIDERS],
  news_search_provider_keys: {},
  news_search_max_results: 10,
  news_search_timeout_seconds: 8,
};

const MARKET_DATA_PROVIDER_CAPABILITY_BASE: Record<
  string,
  Omit<MarketDataProviderCapability, "active" | "configured" | "provider">
> = {
  mock: {
    category: "mock",
    supports_daily_bars: true,
    supports_realtime_quotes: false,
    readiness_note: "Deterministic fixture data for development and tests.",
  },
  yfinance: {
    category: "historical_daily",
    supports_daily_bars: true,
    supports_realtime_quotes: false,
    readiness_note:
      "Historical daily bars are available; real-time quotes are not enabled.",
  },
  akshare: {
    category: "historical_daily",
    supports_daily_bars: true,
    supports_realtime_quotes: false,
    readiness_note:
      "Requires AkShare support to be enabled and dependencies installed.",
  },
  tushare: {
    category: "historical_daily",
    supports_daily_bars: true,
    supports_realtime_quotes: false,
    readiness_note: "Requires a configured Tushare token.",
  },
};

const NEWS_SEARCH_PROVIDER_CAPABILITY_BASE: Record<
  NewsSearchProviderId,
  Omit<
    NewsSearchProviderCapability,
    "provider" | "enabled" | "configured" | "credential_configured" | "priority"
  >
> = {
  anspire: {
    display_name: "Anspire AI Search",
    credential_required: true,
    credential_field: "api_key",
    supported_markets: ["A-share", "US", "HK", "global"],
    supported_regions: ["CN", "US", "HK", "global"],
    supported_result_kinds: ["news", "web", "public_opinion"],
    default_timeout_seconds: 8,
    default_max_results: 10,
    implementation_status: "implemented",
    readiness_note:
      "Bearer-auth search adapter for financial news and public opinion.",
    citation_caveat:
      "Search results become citable only after they are stored as local news.",
  },
  serpapi_baidu: {
    display_name: "SerpAPI Baidu",
    credential_required: true,
    credential_field: "api_key",
    supported_markets: ["A-share", "HK", "China"],
    supported_regions: ["CN"],
    supported_result_kinds: ["news", "web", "social"],
    default_timeout_seconds: 8,
    default_max_results: 10,
    implementation_status: "implemented",
    readiness_note:
      "Baidu search result adapter for Chinese-market news discovery.",
    citation_caveat:
      "Baidu results are collection candidates until stored locally.",
  },
  tavily: {
    display_name: "Tavily",
    credential_required: true,
    credential_field: "api_key",
    supported_markets: ["global"],
    supported_regions: ["global"],
    supported_result_kinds: ["news", "web"],
    default_timeout_seconds: 8,
    default_max_results: 10,
    implementation_status: "configured_only",
    readiness_note:
      "Registry-only in this slice; a direct adapter can follow later.",
    citation_caveat:
      "Do not cite Tavily results until adapter storage is implemented.",
  },
  bocha: {
    display_name: "Bocha Search",
    credential_required: true,
    credential_field: "api_key",
    supported_markets: ["A-share", "China"],
    supported_regions: ["CN"],
    supported_result_kinds: ["news", "web", "ai_summary"],
    default_timeout_seconds: 8,
    default_max_results: 10,
    implementation_status: "needs_contract",
    readiness_note:
      "Chinese search candidate; endpoint contract needs confirmation.",
    citation_caveat:
      "Keep Bocha as registry-only until API and storage terms are reviewed.",
  },
  brave: {
    display_name: "Brave Search",
    credential_required: true,
    credential_field: "subscription_token",
    supported_markets: ["US", "global"],
    supported_regions: ["US", "global"],
    supported_result_kinds: ["news", "web"],
    default_timeout_seconds: 8,
    default_max_results: 10,
    implementation_status: "configured_only",
    readiness_note: "Privacy-oriented search candidate; adapter deferred.",
    citation_caveat:
      "Review plan storage rights before storing Brave result text.",
  },
  minimax: {
    display_name: "MiniMax",
    credential_required: true,
    credential_field: "api_key",
    supported_markets: ["global"],
    supported_regions: ["global"],
    supported_result_kinds: ["structured_search", "web"],
    default_timeout_seconds: 8,
    default_max_results: 10,
    implementation_status: "needs_contract",
    readiness_note:
      "MCP/CLI-oriented search path; backend REST contract is not confirmed.",
    citation_caveat:
      "Keep MiniMax results out of citations until a backend adapter exists.",
  },
  yfinance: {
    display_name: "yfinance",
    credential_required: false,
    credential_field: null,
    supported_markets: ["US", "global"],
    supported_regions: ["US", "global"],
    supported_result_kinds: ["news"],
    default_timeout_seconds: 8,
    default_max_results: 10,
    implementation_status: "existing",
    readiness_note:
      "Existing news ingestion path; not part of live-search MVP.",
    citation_caveat: "Only stored yfinance NewsArticle rows are citable.",
  },
  akshare: {
    display_name: "AkShare",
    credential_required: false,
    credential_field: null,
    supported_markets: ["A-share", "China"],
    supported_regions: ["CN"],
    supported_result_kinds: ["news"],
    default_timeout_seconds: 8,
    default_max_results: 10,
    implementation_status: "existing",
    readiness_note: "Existing CN news ingestion path when AkShare is enabled.",
    citation_caveat: "Only stored AkShare NewsArticle rows are citable.",
  },
  tushare: {
    display_name: "Tushare",
    credential_required: true,
    credential_field: "tushare_token",
    supported_markets: ["A-share", "China"],
    supported_regions: ["CN"],
    supported_result_kinds: ["news"],
    default_timeout_seconds: 8,
    default_max_results: 10,
    implementation_status: "existing",
    readiness_note: "Existing placeholder requires the saved Tushare token.",
    citation_caveat: "Only stored Tushare-backed NewsArticle rows are citable.",
  },
  mock: {
    display_name: "Mock news",
    credential_required: false,
    credential_field: null,
    supported_markets: ["US", "development"],
    supported_regions: ["US"],
    supported_result_kinds: ["news"],
    default_timeout_seconds: 8,
    default_max_results: 10,
    implementation_status: "mock",
    readiness_note:
      "Deterministic local fixture path for development and tests.",
    citation_caveat: "Mock rows are not production evidence.",
  },
};

function settingsPath(): string {
  return join(process.cwd(), "..", "..", "data", "platform_settings.json");
}

async function readSettingsFile(): Promise<Record<string, unknown>> {
  try {
    const raw = await readFile(settingsPath(), "utf-8");
    const parsed: unknown = JSON.parse(raw);
    return typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : {};
  } catch {
    return {};
  }
}

function normalizeStringList(value: unknown): string[] {
  const rawCodes = Array.isArray(value)
    ? value.map((item) => String(item))
    : typeof value === "string"
      ? value.replaceAll(",", "\n").split(/\r?\n/)
      : [];
  const seen = new Set<string>();
  const normalized: string[] = [];

  for (const rawCode of rawCodes) {
    const code = rawCode.trim();
    if (!code || seen.has(code)) {
      continue;
    }
    normalized.push(code);
    seen.add(code);
  }

  return normalized;
}

function normalizeColorScheme(value: unknown): ColorScheme {
  return value === "international" ? "international" : "china";
}

export function normalizeFavoriteMacroIndicatorCodes(value: unknown): string[] {
  return normalizeStringList(value);
}

export function normalizeFavoriteHomeIndexCodes(value: unknown): string[] {
  const normalized = normalizeStringList(value);
  return normalized.length > 0
    ? normalized
    : [...DEFAULT_FAVORITE_HOME_INDEX_CODES];
}

export function normalizeHomeIndexDisplayFields(
  value: unknown,
): HomeIndexDisplayField[] {
  const allowedFields = new Set<string>(HOME_INDEX_DISPLAY_FIELD_VALUES);
  const normalized = normalizeStringList(value).filter(
    (field): field is HomeIndexDisplayField => allowedFields.has(field),
  );
  return normalized.length > 0
    ? normalized
    : [...DEFAULT_HOME_INDEX_DISPLAY_FIELDS];
}

function normalizeNewsSearchProviderIds(
  value: unknown,
): NewsSearchProviderId[] {
  const allowedProviders = new Set<string>(NEWS_SEARCH_PROVIDER_IDS);
  const rawProviders = normalizeStringList(value);
  return rawProviders.filter((provider): provider is NewsSearchProviderId =>
    allowedProviders.has(provider),
  );
}

export function normalizeNewsSearchProviderOrder(
  value: unknown,
): NewsSearchProviderId[] {
  const normalized = normalizeNewsSearchProviderIds(value);
  const ordered =
    normalized.length > 0
      ? normalized
      : [...DEFAULT_NEWS_SEARCH_PROVIDER_ORDER];
  for (const provider of NEWS_SEARCH_PROVIDER_IDS) {
    if (!ordered.includes(provider)) {
      ordered.push(provider);
    }
  }
  return ordered;
}

export function normalizeNewsSearchEnabledProviders(
  value: unknown,
): NewsSearchProviderId[] {
  if (value === undefined || value === null) {
    return [...DEFAULT_NEWS_SEARCH_ENABLED_PROVIDERS];
  }
  return normalizeNewsSearchProviderIds(value);
}

function normalizeNewsSearchProviderKeys(
  value: unknown,
): Record<string, string> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {};
  }

  const payload = value as Record<string, unknown>;
  const keys: Record<string, string> = {};
  for (const provider of NEWS_SEARCH_PROVIDER_IDS) {
    const rawValue = payload[provider];
    if (rawValue === undefined || rawValue === null) {
      continue;
    }
    const textValue = String(rawValue).trim();
    if (textValue) {
      keys[provider] = textValue;
    }
  }
  return keys;
}

function mergeNewsSearchProviderKeys(
  current: Record<string, string>,
  updates: unknown,
): Record<string, string> {
  const merged = normalizeNewsSearchProviderKeys(current);
  if (!updates || typeof updates !== "object" || Array.isArray(updates)) {
    return merged;
  }

  const payload = updates as Record<string, unknown>;
  for (const provider of NEWS_SEARCH_PROVIDER_IDS) {
    if (!(provider in payload)) {
      continue;
    }
    const textValue = String(payload[provider] ?? "").trim();
    if (textValue) {
      merged[provider] = textValue;
    }
  }
  return merged;
}

function normalizeBoundedNumber(
  value: unknown,
  fallback: number,
  min: number,
  max: number,
): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  return Math.min(Math.max(parsed, min), max);
}

function buildStoredPlatformSettings(
  stored: Record<string, unknown>,
): StoredPlatformSettings {
  const storedLlmApiBase =
    typeof stored.llm_api_base === "string"
      ? normalizeLlmApiBase(stored.llm_api_base)
      : "";
  const hasExplicitStoredLlmApiBase =
    stored.llm_api_base !== undefined && stored.llm_api_base !== null;
  const hasInvalidStoredLlmApiBase = Boolean(
    hasExplicitStoredLlmApiBase &&
      (typeof stored.llm_api_base !== "string" ||
        (storedLlmApiBase && !isValidLlmApiBase(storedLlmApiBase))),
  );
  const llmApiBase = isValidLlmApiBase(storedLlmApiBase)
    ? storedLlmApiBase
    : DEFAULTS.llm_api_base;
  const storedLlmProvider =
    typeof stored.llm_provider === "string"
      ? stored.llm_provider.trim().toLowerCase()
      : DEFAULTS.llm_provider;
  const storedLlmApiKey =
    typeof stored.llm_api_key === "string"
      ? stored.llm_api_key
      : DEFAULTS.llm_api_key;
  return {
    market_data_provider:
      typeof stored.market_data_provider === "string"
        ? stored.market_data_provider
        : DEFAULTS.market_data_provider,
    llm_provider:
      hasInvalidStoredLlmApiBase || storedLlmProvider !== "openai"
        ? "mock"
        : "openai",
    llm_api_key: hasInvalidStoredLlmApiBase ? "" : storedLlmApiKey,
    llm_api_base: llmApiBase,
    llm_model:
      (typeof stored.llm_model === "string"
        ? normalizeLlmModel(stored.llm_model)
        : "") || DEFAULTS.llm_model,
    akshare_enabled:
      typeof stored.akshare_enabled === "boolean"
        ? stored.akshare_enabled
        : DEFAULTS.akshare_enabled,
    tushare_token:
      typeof stored.tushare_token === "string"
        ? stored.tushare_token
        : DEFAULTS.tushare_token,
    tushare_http_url:
      typeof stored.tushare_http_url === "string"
        ? stored.tushare_http_url
        : DEFAULTS.tushare_http_url,
    color_scheme: normalizeColorScheme(
      stored.color_scheme ?? DEFAULTS.color_scheme,
    ),
    favorite_home_index_codes:
      stored.favorite_home_index_codes === undefined
        ? DEFAULTS.favorite_home_index_codes
        : normalizeFavoriteHomeIndexCodes(stored.favorite_home_index_codes),
    home_index_display_fields:
      stored.home_index_display_fields === undefined
        ? DEFAULTS.home_index_display_fields
        : normalizeHomeIndexDisplayFields(stored.home_index_display_fields),
    favorite_macro_indicator_codes:
      stored.favorite_macro_indicator_codes === undefined
        ? DEFAULTS.favorite_macro_indicator_codes
        : normalizeFavoriteMacroIndicatorCodes(
            stored.favorite_macro_indicator_codes,
          ),
    news_search_provider_order:
      stored.news_search_provider_order === undefined
        ? DEFAULTS.news_search_provider_order
        : normalizeNewsSearchProviderOrder(stored.news_search_provider_order),
    news_search_enabled_providers:
      stored.news_search_enabled_providers === undefined
        ? DEFAULTS.news_search_enabled_providers
        : normalizeNewsSearchEnabledProviders(
            stored.news_search_enabled_providers,
          ),
    news_search_provider_keys: normalizeNewsSearchProviderKeys(
      stored.news_search_provider_keys ?? DEFAULTS.news_search_provider_keys,
    ),
    news_search_max_results: normalizeBoundedNumber(
      stored.news_search_max_results ?? DEFAULTS.news_search_max_results,
      DEFAULTS.news_search_max_results,
      1,
      20,
    ),
    news_search_timeout_seconds: normalizeBoundedNumber(
      stored.news_search_timeout_seconds ??
        DEFAULTS.news_search_timeout_seconds,
      DEFAULTS.news_search_timeout_seconds,
      1,
      30,
    ),
  };
}

function isMarketDataProviderConfigured(
  provider: string,
  settings: StoredPlatformSettings,
): boolean {
  if (provider === "mock" || provider === "yfinance") {
    return true;
  }
  if (provider === "akshare") {
    return settings.akshare_enabled;
  }
  if (provider === "tushare") {
    return Boolean(settings.tushare_token.trim());
  }
  return false;
}

function buildMarketDataProviderCapabilities(
  settings: StoredPlatformSettings,
): MarketDataProviderCapability[] {
  const activeProvider = settings.market_data_provider.toLowerCase();
  return Object.entries(MARKET_DATA_PROVIDER_CAPABILITY_BASE).map(
    ([provider, baseCapability]) => ({
      provider,
      active: provider === activeProvider,
      configured: isMarketDataProviderConfigured(provider, settings),
      ...baseCapability,
    }),
  );
}

function isNewsSearchProviderConfigured(
  provider: NewsSearchProviderId,
  settings: StoredPlatformSettings,
): boolean {
  if (provider === "akshare") {
    return settings.akshare_enabled;
  }
  if (provider === "tushare") {
    return Boolean(settings.tushare_token.trim());
  }
  const capability = NEWS_SEARCH_PROVIDER_CAPABILITY_BASE[provider];
  if (!capability.credential_required) {
    return true;
  }
  return Boolean(settings.news_search_provider_keys[provider]?.trim());
}

function buildNewsSearchProviderCapabilities(
  settings: StoredPlatformSettings,
): NewsSearchProviderCapability[] {
  const enabledProviders = new Set(settings.news_search_enabled_providers);
  return settings.news_search_provider_order.map((provider, index) => {
    const configured = isNewsSearchProviderConfigured(provider, settings);
    const baseCapability = NEWS_SEARCH_PROVIDER_CAPABILITY_BASE[provider];
    return {
      provider,
      enabled: enabledProviders.has(provider),
      configured,
      credential_configured: baseCapability.credential_required
        ? configured
        : true,
      priority: index + 1,
      ...baseCapability,
    };
  });
}

function buildNewsSearchProviderKeyConfiguredFlags(
  settings: StoredPlatformSettings,
): Record<string, boolean> {
  const flags: Record<string, boolean> = {};
  for (const provider of NEWS_SEARCH_PROVIDER_IDS) {
    if (settings.news_search_provider_keys[provider]?.trim()) {
      flags[provider] = true;
    }
  }
  return flags;
}

function toPublicPlatformSettings(
  settings: StoredPlatformSettings,
): PlatformSettings {
  return {
    ...settings,
    llm_api_key: "",
    tushare_token: "",
    news_search_provider_keys: {},
    llm_api_key_configured: Boolean(settings.llm_api_key.trim()),
    tushare_token_configured: Boolean(settings.tushare_token.trim()),
    news_search_provider_keys_configured:
      buildNewsSearchProviderKeyConfiguredFlags(settings),
    market_data_provider_capabilities:
      buildMarketDataProviderCapabilities(settings),
    news_search_provider_capabilities:
      buildNewsSearchProviderCapabilities(settings),
  };
}

async function getStoredPlatformSettings(): Promise<StoredPlatformSettings> {
  const stored = await readSettingsFile();
  return buildStoredPlatformSettings(stored);
}

export async function getPlatformSettings(): Promise<PlatformSettings> {
  return toPublicPlatformSettings(await getStoredPlatformSettings());
}

export type PlatformSettingsUpdate = Partial<
  Omit<
    StoredPlatformSettings,
    | "favorite_macro_indicator_codes"
    | "favorite_home_index_codes"
    | "home_index_display_fields"
    | "news_search_provider_order"
    | "news_search_enabled_providers"
    | "news_search_provider_keys"
    | "news_search_max_results"
    | "news_search_timeout_seconds"
  >
> & {
  favorite_macro_indicator_codes?: unknown;
  favorite_home_index_codes?: unknown;
  home_index_display_fields?: unknown;
  news_search_provider_order?: unknown;
  news_search_enabled_providers?: unknown;
  news_search_provider_keys?: unknown;
  news_search_max_results?: unknown;
  news_search_timeout_seconds?: unknown;
};

export function isPlatformSettingsUpdatePayload(
  value: unknown,
): value is PlatformSettingsUpdate {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export class PlatformSettingsValidationError extends Error {
  constructor(
    readonly code:
      | "invalid_provider"
      | "invalid_base"
      | "invalid_model"
      | "invalid_key",
    readonly field:
      | "llm_provider"
      | "llm_api_base"
      | "llm_model"
      | "llm_api_key",
    message: string,
  ) {
    super(message);
    this.name = "PlatformSettingsValidationError";
  }
}

function normalizeLlmProviderUpdate(value: unknown): "mock" | "openai" {
  if (typeof value !== "string") {
    throw new PlatformSettingsValidationError(
      "invalid_provider",
      "llm_provider",
      "llm_provider must be 'mock' or 'openai'",
    );
  }
  const normalized = value.trim().toLowerCase();
  if (normalized !== "mock" && normalized !== "openai") {
    throw new PlatformSettingsValidationError(
      "invalid_provider",
      "llm_provider",
      "llm_provider must be 'mock' or 'openai'",
    );
  }
  return normalized;
}

function normalizeLlmApiBaseUpdate(value: unknown): string {
  if (typeof value !== "string") {
    throw new PlatformSettingsValidationError(
      "invalid_base",
      "llm_api_base",
      "llm_api_base must be an absolute HTTP(S) URL without credentials, query, or fragment",
    );
  }
  const normalized = normalizeLlmApiBase(value);
  if (!isValidLlmApiBase(normalized)) {
    throw new PlatformSettingsValidationError(
      "invalid_base",
      "llm_api_base",
      "llm_api_base must be an absolute HTTP(S) URL without credentials, query, or fragment",
    );
  }
  return normalized;
}

function normalizeLlmModelUpdate(value: unknown): string {
  if (typeof value !== "string") {
    throw new PlatformSettingsValidationError(
      "invalid_model",
      "llm_model",
      "llm_model must contain 1 to 128 characters",
    );
  }
  const normalized = normalizeLlmModel(value);
  if (!normalized || normalized.length > 128) {
    throw new PlatformSettingsValidationError(
      "invalid_model",
      "llm_model",
      "llm_model must contain 1 to 128 characters",
    );
  }
  return normalized;
}

function resolveLlmApiKeyUpdate(value: unknown, current: string): string {
  if (value === undefined || value === null) {
    return current;
  }
  if (typeof value !== "string") {
    throw new PlatformSettingsValidationError(
      "invalid_key",
      "llm_api_key",
      "llm_api_key must be a string",
    );
  }
  return value.trim() ? value : current;
}

export async function savePlatformSettings(
  updates: PlatformSettingsUpdate,
): Promise<PlatformSettings> {
  const current = await getStoredPlatformSettings();
  const nextLlmApiBase =
    updates.llm_api_base === undefined
      ? current.llm_api_base
      : normalizeLlmApiBaseUpdate(updates.llm_api_base);
  const resolvedLlmApiKey = resolveLlmApiKeyUpdate(
    updates.llm_api_key,
    current.llm_api_key,
  );
  const hasReplacementLlmApiKey =
    typeof updates.llm_api_key === "string" &&
    Boolean(updates.llm_api_key.trim());
  const next: StoredPlatformSettings = {
    market_data_provider:
      updates.market_data_provider ?? current.market_data_provider,
    llm_provider:
      updates.llm_provider === undefined
        ? current.llm_provider
        : normalizeLlmProviderUpdate(updates.llm_provider),
    llm_api_key:
      nextLlmApiBase !== current.llm_api_base && !hasReplacementLlmApiKey
        ? ""
        : resolvedLlmApiKey,
    llm_api_base: nextLlmApiBase,
    llm_model:
      updates.llm_model === undefined
        ? current.llm_model
        : normalizeLlmModelUpdate(updates.llm_model),
    akshare_enabled: updates.akshare_enabled ?? current.akshare_enabled,
    tushare_token:
      updates.tushare_token !== undefined && updates.tushare_token.trim()
        ? updates.tushare_token
        : current.tushare_token,
    tushare_http_url: updates.tushare_http_url ?? current.tushare_http_url,
    color_scheme: normalizeColorScheme(
      updates.color_scheme ?? current.color_scheme,
    ),
    favorite_home_index_codes:
      updates.favorite_home_index_codes === undefined
        ? current.favorite_home_index_codes
        : normalizeFavoriteHomeIndexCodes(updates.favorite_home_index_codes),
    home_index_display_fields:
      updates.home_index_display_fields === undefined
        ? current.home_index_display_fields
        : normalizeHomeIndexDisplayFields(updates.home_index_display_fields),
    favorite_macro_indicator_codes:
      updates.favorite_macro_indicator_codes === undefined
        ? current.favorite_macro_indicator_codes
        : normalizeFavoriteMacroIndicatorCodes(
            updates.favorite_macro_indicator_codes,
          ),
    news_search_provider_order:
      updates.news_search_provider_order === undefined
        ? current.news_search_provider_order
        : normalizeNewsSearchProviderOrder(updates.news_search_provider_order),
    news_search_enabled_providers:
      updates.news_search_enabled_providers === undefined
        ? current.news_search_enabled_providers
        : normalizeNewsSearchEnabledProviders(
            updates.news_search_enabled_providers,
          ),
    news_search_provider_keys:
      updates.news_search_provider_keys === undefined
        ? current.news_search_provider_keys
        : mergeNewsSearchProviderKeys(
            current.news_search_provider_keys,
            updates.news_search_provider_keys,
          ),
    news_search_max_results:
      updates.news_search_max_results === undefined
        ? current.news_search_max_results
        : normalizeBoundedNumber(updates.news_search_max_results, 10, 1, 20),
    news_search_timeout_seconds:
      updates.news_search_timeout_seconds === undefined
        ? current.news_search_timeout_seconds
        : normalizeBoundedNumber(updates.news_search_timeout_seconds, 8, 1, 30),
  };

  const path = settingsPath();
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, JSON.stringify(next, null, 2), "utf-8");
  return toPublicPlatformSettings(next);
}
