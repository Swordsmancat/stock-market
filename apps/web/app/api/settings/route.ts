import { getPlatformSettings, savePlatformSettings } from "@/lib/platform-settings-store";

type PlatformSettingsRoutePayload = {
  market_data_provider?: string;
  llm_provider?: string;
  llm_api_key?: string;
  llm_api_base?: string;
  akshare_enabled?: boolean;
  tushare_token?: string;
  llm_api_key_configured?: boolean;
  tushare_token_configured?: boolean;
  market_data_provider_capabilities?: unknown;
};

function buildPublicSettingsPayload(settings: PlatformSettingsRoutePayload): PlatformSettingsRoutePayload {
  const llmApiKey = typeof settings.llm_api_key === "string" ? settings.llm_api_key : "";
  const tushareToken = typeof settings.tushare_token === "string" ? settings.tushare_token : "";

  return {
    ...settings,
    llm_api_key_configured: settings.llm_api_key_configured ?? Boolean(llmApiKey.trim()),
    tushare_token: "",
    tushare_token_configured: settings.tushare_token_configured ?? Boolean(tushareToken.trim()),
  };
}

export async function GET() {
  const settings = await getPlatformSettings();
  return Response.json({ source: "platform_settings", ...buildPublicSettingsPayload(settings) });
}

export async function PUT(request: Request) {
  const body = (await request.json()) as {
    market_data_provider?: string;
    llm_provider?: string;
    llm_api_key?: string;
    llm_api_base?: string;
    akshare_enabled?: boolean;
    tushare_token?: string;
  };
  const saved = await savePlatformSettings(body);
  return Response.json({ source: "platform_settings", ...buildPublicSettingsPayload(saved) });
}
