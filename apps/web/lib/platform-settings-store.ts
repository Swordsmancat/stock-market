import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";

/** Shared with Python backend at repo/data/platform_settings.json */

export type PlatformSettings = {
  market_data_provider: string;
  llm_provider: string;
  llm_api_key: string;
  llm_api_base: string;
  akshare_enabled: boolean;
  tushare_token: string;
};

const DEFAULTS: PlatformSettings = {
  market_data_provider: process.env.NEXT_PUBLIC_MARKET_DATA_PROVIDER ?? "yfinance",
  llm_provider: process.env.LLM_PROVIDER ?? "mock",
  llm_api_key: process.env.LLM_API_KEY ?? "",
  llm_api_base: "https://api.openai.com/v1",
  akshare_enabled: false,
  tushare_token: "",
};

function settingsPath(): string {
  return join(process.cwd(), "..", "..", "data", "platform_settings.json");
}

async function readSettingsFile(): Promise<Partial<PlatformSettings>> {
  try {
    const raw = await readFile(settingsPath(), "utf-8");
    return JSON.parse(raw) as Partial<PlatformSettings>;
  } catch {
    return {};
  }
}

export async function getPlatformSettings(): Promise<PlatformSettings & { llm_api_key_configured: boolean }> {
  const stored = await readSettingsFile();
  const merged: PlatformSettings = {
    market_data_provider: stored.market_data_provider ?? DEFAULTS.market_data_provider,
    llm_provider: stored.llm_provider ?? DEFAULTS.llm_provider,
    llm_api_key: stored.llm_api_key ?? DEFAULTS.llm_api_key,
    llm_api_base: stored.llm_api_base ?? DEFAULTS.llm_api_base,
    akshare_enabled: stored.akshare_enabled ?? DEFAULTS.akshare_enabled,
    tushare_token: stored.tushare_token ?? DEFAULTS.tushare_token,
  };
  return {
    ...merged,
    llm_api_key_configured: Boolean(merged.llm_api_key.trim()),
  };
}

export async function savePlatformSettings(updates: Partial<PlatformSettings>): Promise<PlatformSettings> {
  const current = await getPlatformSettings();
  const next: PlatformSettings = {
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
  };

  const path = settingsPath();
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, JSON.stringify(next, null, 2), "utf-8");
  return next;
}
