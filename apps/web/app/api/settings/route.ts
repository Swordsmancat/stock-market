import {
  getPlatformSettings,
  isPlatformSettingsUpdatePayload,
  PlatformSettingsValidationError,
  savePlatformSettings,
} from "@/lib/platform-settings-store";

type PlatformSettingsRoutePayload = {
  market_data_provider?: string;
  llm_provider?: string;
  llm_api_key?: string;
  llm_api_base?: string;
  llm_model?: string;
  akshare_enabled?: boolean;
  tushare_token?: string;
  tushare_http_url?: string;
  color_scheme?: "china" | "international";
  favorite_home_index_codes?: string[];
  home_index_display_fields?: string[];
  favorite_macro_indicator_codes?: string[];
  news_search_provider_order?: string[];
  news_search_enabled_providers?: string[];
  news_search_provider_keys?: Record<string, string>;
  news_search_max_results?: number;
  news_search_timeout_seconds?: number;
  llm_api_key_configured?: boolean;
  tushare_token_configured?: boolean;
  news_search_provider_keys_configured?: Record<string, boolean>;
  market_data_provider_capabilities?: unknown;
  news_search_provider_capabilities?: unknown;
};

function buildPublicSettingsPayload(
  settings: PlatformSettingsRoutePayload,
): PlatformSettingsRoutePayload {
  const llmApiKey =
    typeof settings.llm_api_key === "string" ? settings.llm_api_key : "";
  const tushareToken =
    typeof settings.tushare_token === "string" ? settings.tushare_token : "";
  const newsSearchProviderKeys =
    settings.news_search_provider_keys &&
    typeof settings.news_search_provider_keys === "object"
      ? settings.news_search_provider_keys
      : {};

  return {
    ...settings,
    llm_api_key: "",
    llm_api_key_configured:
      settings.llm_api_key_configured ?? Boolean(llmApiKey.trim()),
    tushare_token: "",
    tushare_token_configured:
      settings.tushare_token_configured ?? Boolean(tushareToken.trim()),
    news_search_provider_keys: {},
    news_search_provider_keys_configured:
      settings.news_search_provider_keys_configured ??
      Object.fromEntries(
        Object.entries(newsSearchProviderKeys)
          .filter(([, value]) => value.trim())
          .map(([key]) => [key, true]),
      ),
  };
}

export async function GET() {
  const settings = await getPlatformSettings();
  return Response.json({
    source: "platform_settings",
    ...buildPublicSettingsPayload(settings),
  });
}

export async function PUT(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    body = null;
  }
  if (!isPlatformSettingsUpdatePayload(body)) {
    return Response.json(
      {
        code: "invalid_payload",
        field: "body",
        detail: "Platform settings payload must be a JSON object.",
      },
      { status: 422 },
    );
  }
  try {
    const saved = await savePlatformSettings(body);
    return Response.json({
      source: "platform_settings",
      ...buildPublicSettingsPayload(saved),
    });
  } catch (error) {
    if (error instanceof PlatformSettingsValidationError) {
      return Response.json(
        { code: error.code, field: error.field, detail: error.message },
        { status: 422 },
      );
    }
    throw error;
  }
}
