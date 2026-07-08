import { getTranslations } from "next-intl/server";

import { savePlatformSettingsAction } from "@/app/[locale]/actions";
import { FlashBanner } from "@/components/flash-banner";
import { FinancialPageHeader } from "@/components/financial-page-header";
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
  const displayColorScheme =
    settings.color_scheme === "international" ? t("internationalConvention") : t("chinaConvention");

  return (
    <div className="space-y-6">
      {saved === "ok" ? <FlashBanner variant="success" message={t("saveSuccess")} /> : null}
      {saved === "error" ? <FlashBanner variant="error" message={t("saveFailed")} /> : null}

      <form action={savePlatformSettingsAction} className="space-y-4">
        <input type="hidden" name="locale" value={locale} />

        <FinancialPageHeader
          title={t("title")}
          description={t("description")}
          badges={[
            { label: t("displayPreferencesTitle"), variant: "secondary" },
            { label: t("activeProvider") + `: ${settings.market_data_provider}` },
          ]}
          metrics={[
            {
              label: t("dataProviderTitle"),
              value: settings.market_data_provider,
              description: settings.market_data_provider_capabilities.find(
                (capability) => capability.provider === settings.market_data_provider,
              )?.configured
                ? t("providerConfigured")
                : t("providerNeedsSetup"),
            },
            {
              label: t("colorSchemeLabel"),
              value: displayColorScheme,
              description: t("displayPreferencesTitle"),
            },
            {
              label: t("llmProvider"),
              value: settings.llm_provider,
              description: settings.llm_api_key_configured ? t("providerConfigured") : t("providerNeedsSetup"),
            },
            {
              label: t("macroFavoritesTitle"),
              value: settings.favorite_macro_indicator_codes.length,
              description: t("macroFavoritesLabel"),
            },
          ]}
          actions={
            <Button type="submit" size="sm">
              {t("save")}
            </Button>
          }
        />

        <div className="grid gap-4 xl:grid-cols-2">
          <Card className="rounded-md shadow-none">
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

        <Card className="rounded-md shadow-none">
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

        <Card className="rounded-md shadow-none">
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

        <Card className="rounded-md shadow-none">
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

        <Card className="rounded-md shadow-none">
          <CardHeader>
            <CardTitle>{t("displayPreferencesTitle")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("colorSchemeLabel")}</label>
              <div className="space-y-3">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="radio"
                    name="color_scheme"
                    value="china"
                    defaultChecked={settings.color_scheme === "china"}
                    className="h-4 w-4"
                  />
                  <div className="flex items-center gap-2">
                    <span className="text-sm">{t("chinaConvention")}</span>
                    <span className="text-xs text-muted-foreground">
                      (<span className="text-green-600 font-medium">{t("greenUp")}</span> /{" "}
                      <span className="text-red-600 font-medium">{t("redDown")}</span>)
                    </span>
                  </div>
                </label>
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="radio"
                    name="color_scheme"
                    value="international"
                    defaultChecked={settings.color_scheme === "international"}
                    className="h-4 w-4"
                  />
                  <div className="flex items-center gap-2">
                    <span className="text-sm">{t("internationalConvention")}</span>
                    <span className="text-xs text-muted-foreground">
                      (<span className="text-red-600 font-medium">{t("redUp")}</span> /{" "}
                      <span className="text-green-600 font-medium">{t("greenDown")}</span>)
                    </span>
                  </div>
                </label>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-md shadow-none xl:col-span-2">
          <CardHeader>
            <CardTitle>{t("macroFavoritesTitle")}</CardTitle>
            <CardDescription>{t("macroFavoritesDesc")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <label className="text-sm font-medium" htmlFor="favorite_macro_indicator_codes">
              {t("macroFavoritesLabel")}
            </label>
            <textarea
              id="favorite_macro_indicator_codes"
              name="favorite_macro_indicator_codes"
              defaultValue={settings.favorite_macro_indicator_codes.join("\n")}
              rows={8}
              className="min-h-36 w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">{t("macroFavoritesHint")}</p>
            <p className="text-xs text-muted-foreground">{t("macroFavoritesDefault")}</p>
          </CardContent>
        </Card>
        </div>

        <Button type="submit">{t("save")}</Button>
      </form>
    </div>
  );
}
