import { getPlatformSettings, savePlatformSettings } from "@/lib/platform-settings-store";

export async function GET() {
  const settings = await getPlatformSettings();
  return Response.json({ source: "platform_settings", ...settings });
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
  return Response.json({ source: "platform_settings", ...saved, llm_api_key_configured: Boolean(saved.llm_api_key.trim()) });
}
