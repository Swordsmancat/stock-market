import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";

/** Shared with Python backend at repo/data/platform_settings.json */

export type ColorScheme = "china" | "international";

export type PlatformSettings = {
  market_data_provider: string;
  llm_provider: string;
  llm_api_key: string;
  llm_api_base: string;
  akshare_enabled: boolean;
  tushare_token: string;
  tushare_http_url: string;
  color_scheme: ColorScheme;
  llm_api_key_configured: boolean;
  tushare_token_configured: boolean;
  market_data_provider_capabilities: MarketDataProviderCapability[];
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

type StoredPlatformSettings = Omit<
  PlatformSettings,
  "llm_api_key_configured" | "tushare_token_configured" | "market_data_provider_capabilities"
>;

const DEFAULTS: StoredPlatformSettings = {
  market_data_provider: process.env.NEXT_PUBLIC_MARKET_DATA_PROVIDER ?? "yfinance",
  llm_provider: process.env.LLM_PROVIDER ?? "mock",
  llm_api_key: process.env.LLM_API_KEY ?? "",
  llm_api_base: "https://api.openai.com/v1",
  akshare_enabled: false,
  tushare_token: "",
  tushare_http_url: "",
  color_scheme: "china",
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
    readiness_note: "Historical daily bars are available; real-time quotes are not enabled.",
  },
  akshare: {
    category: "historical_daily",
    supports_daily_bars: true,
    supports_realtime_quotes: false,
    readiness_note: "Requires AkShare support to be enabled and dependencies installed.",
  },
  tushare: {
    category: "historical_daily",
    supports_daily_bars: true,
    supports_realtime_quotes: false,
    readiness_note: "Requires a configured Tushare token.",
  },
};

function settingsPath(): string {
  return join(process.cwd(), "..", "..", "data", "platform_settings.json");
}

async function readSettingsFile(): Promise<Partial<StoredPlatformSettings>> {
  try {
    const raw = await readFile(settingsPath(), "utf-8");
    return JSON.parse(raw) as Partial<StoredPlatformSettings>;
  } catch {
    return {};
  }
}

function normalizeColorScheme(value: unknown): ColorScheme {
  return value === "international" ? "international" : "china";
}

function buildStoredPlatformSettings(stored: Partial<StoredPlatformSettings>): StoredPlatformSettings {
  return {
    market_data_provider: stored.market_data_provider ?? DEFAULTS.market_data_provider,
    llm_provider: stored.llm_provider ?? DEFAULTS.llm_provider,
    llm_api_key: stored.llm_api_key ?? DEFAULTS.llm_api_key,
    llm_api_base: stored.llm_api_base ?? DEFAULTS.llm_api_base,
    akshare_enabled: stored.akshare_enabled ?? DEFAULTS.akshare_enabled,
    tushare_token: stored.tushare_token ?? DEFAULTS.tushare_token,
    tushare_http_url: stored.tushare_http_url ?? DEFAULTS.tushare_http_url,
    color_scheme: normalizeColorScheme(stored.color_scheme ?? DEFAULTS.color_scheme),
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
  return Object.entries(MARKET_DATA_PROVIDER_CAPABILITY_BASE).map(([provider, baseCapability]) => ({
    provider,
    active: provider === activeProvider,
    configured: isMarketDataProviderConfigured(provider, settings),
    ...baseCapability,
  }));
}

function toPublicPlatformSettings(settings: StoredPlatformSettings): PlatformSettings {
  return {
    ...settings,
    tushare_token: "",
    llm_api_key_configured: Boolean(settings.llm_api_key.trim()),
    tushare_token_configured: Boolean(settings.tushare_token.trim()),
    market_data_provider_capabilities: buildMarketDataProviderCapabilities(settings),
  };
}

async function getStoredPlatformSettings(): Promise<StoredPlatformSettings> {
  const stored = await readSettingsFile();
  return buildStoredPlatformSettings(stored);
}

export async function getPlatformSettings(): Promise<PlatformSettings> {
  return toPublicPlatformSettings(await getStoredPlatformSettings());
}

export async function savePlatformSettings(updates: Partial<StoredPlatformSettings>): Promise<PlatformSettings> {
  const current = await getStoredPlatformSettings();
  const next: StoredPlatformSettings = {
    market_data_provider: updates.market_data_provider ?? current.market_data_provider,
    llm_provider: updates.llm_provider ?? current.llm_provider,
    llm_api_key:
      updates.llm_api_key !== undefined && updates.llm_api_key.trim()
        ? updates.llm_api_key
        : current.llm_api_key,
    llm_api_base: updates.llm_api_base ?? current.llm_api_base,
    akshare_enabled: updates.akshare_enabled ?? current.akshare_enabled,
    tushare_token:
      updates.tushare_token !== undefined && updates.tushare_token.trim()
        ? updates.tushare_token
        : current.tushare_token,
    tushare_http_url: updates.tushare_http_url ?? current.tushare_http_url,
    color_scheme: normalizeColorScheme(updates.color_scheme ?? current.color_scheme),
  };

  const path = settingsPath();
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, JSON.stringify(next, null, 2), "utf-8");
  return toPublicPlatformSettings(next);
}
