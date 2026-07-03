import { getTranslations } from "next-intl/server";

import { savePlatformSettingsAction } from "@/app/[locale]/actions";
import { FlashBanner } from "@/components/flash-banner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getPlatformSettings } from "@/lib/platform-settings-store";

export default async function SettingsPage({
  params,
  searchParams = Promise.resolve({}),
}: {
  params: Promise<{ locale: string }>;
  searchParams?: Promise<{ saved?: string }>;
}) {
  const { locale } = await params;
  const { saved } = await searchParams;
  const settings = await getPlatformSettings();
  const t = await getTranslations("Settings");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      {saved === "ok" ? <FlashBanner variant="success" message={t("saveSuccess")} /> : null}
      {saved === "error" ? <FlashBanner variant="error" message={t("saveFailed")} /> : null}

      <form action={savePlatformSettingsAction} className="space-y-6">
        <input type="hidden" name="locale" value={locale} />

        <Card>
          <CardHeader>
            <CardTitle>{t("dataProviderTitle")}</CardTitle>
            <CardDescription>{t("dataProviderDesc")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <select
              name="market_data_provider"
              defaultValue={settings.market_data_provider}
              className="flex h-10 w-full max-w-sm rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="yfinance">yfinance</option>
              <option value="akshare">akshare</option>
              <option value="tushare">tushare</option>
              <option value="mock">mock</option>
            </select>
            <p className="text-sm text-muted-foreground">
              {t("activeProvider")}: <span className="font-medium text-foreground">{settings.market_data_provider}</span>
            </p>
            <div className="grid gap-3 md:grid-cols-2">
              {settings.market_data_provider_capabilities.map((capability) => (
                <div key={capability.provider} className="rounded-lg border p-3 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <div className="font-medium">{capability.provider}</div>
                    <span
                      className={
                        capability.configured
                          ? "rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700"
                          : "rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-800"
                      }
                    >
                      {capability.configured ? t("providerConfigured") : t("providerNeedsSetup")}
                    </span>
                  </div>
                  <div className="mt-2 text-muted-foreground">
                    {capability.active ? `${t("providerActive")}. ` : ""}
                    {capability.supports_daily_bars ? t("dailyBarsSupported") : t("dailyBarsUnsupported")}
                    {" "}
                    {capability.supports_realtime_quotes
                      ? t("realtimeQuotesSupported")
                      : t("realtimeQuotesUnsupported")}
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {capability.provider === "mock" ? t("mockReadiness") : null}
                    {capability.provider === "yfinance" ? t("yfinanceReadiness") : null}
                    {capability.provider === "akshare" ? t("akshareReadiness") : null}
                    {capability.provider === "tushare" ? t("tushareReadiness") : null}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("akshareTitle")}</CardTitle>
            <CardDescription>{t("akshareDesc")}</CardDescription>
          </CardHeader>
          <CardContent>
            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                name="akshare_enabled"
                defaultChecked={settings.akshare_enabled}
                className="h-4 w-4 rounded border-gray-300"
              />
              <span className="text-sm">{t("akshareEnableLabel")}</span>
            </label>
            <p className="mt-2 text-xs text-muted-foreground">{t("akshareHint")}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("tushareTitle")}</CardTitle>
            <CardDescription>{t("tushareDesc")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="tushare_token">
                {t("tushareToken")}
              </label>
              <Input
                id="tushare_token"
                name="tushare_token"
                type="password"
                defaultValue=""
                placeholder={
                  settings.tushare_token_configured ? t("tushareTokenConfigured") : t("tushareTokenPlaceholder")
                }
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="tushare_http_url">
                {t("tushareHttpUrl")}
              </label>
              <Input
                id="tushare_http_url"
                name="tushare_http_url"
                defaultValue={settings.tushare_http_url}
                placeholder="http://api.tushare.pro (optional)"
              />
            </div>
            <p className="text-xs text-muted-foreground">{t("tushareHint")}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("llmTitle")}</CardTitle>
            <CardDescription>{t("llmDesc")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="llm_provider">
                {t("llmProvider")}
              </label>
              <select
                id="llm_provider"
                name="llm_provider"
                defaultValue={settings.llm_provider}
                className="flex h-10 w-full max-w-sm rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="mock">mock</option>
                <option value="openai">openai</option>
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="llm_api_base">
                {t("llmApiBase")}
              </label>
              <Input
                id="llm_api_base"
                name="llm_api_base"
                defaultValue={settings.llm_api_base}
                placeholder="https://api.openai.com/v1"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="llm_api_key">
                {t("llmApiKey")}
              </label>
              <Input
                id="llm_api_key"
                name="llm_api_key"
                type="password"
                defaultValue={settings.llm_api_key}
                placeholder={
                  settings.llm_api_key_configured ? t("llmApiKeyConfigured") : t("llmApiKeyPlaceholder")
                }
              />
            </div>
          </CardContent>
        </Card>

        <Button type="submit">{t("save")}</Button>
      </form>
    </div>
  );
}
