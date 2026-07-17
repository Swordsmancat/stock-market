import { getTranslations } from "next-intl/server";

import { savePlatformSettingsAction } from "@/app/[locale]/actions";
import { FlashBanner } from "@/components/flash-banner";
import { FinancialPageHeader } from "@/components/financial-page-header";
import { LlmSettingsControl } from "@/components/llm-settings-control";
import {
  FinancialTerminalCard,
  FinancialTerminalCardContent,
  FinancialTerminalCardHeader,
  FinancialTerminalSurface,
} from "@/components/financial-terminal-section";
import { CardDescription, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  inferLlmApiPreset,
  normalizeLlmApiPresetId,
  type LlmApiPresetId,
  type LlmConfigErrorCode,
} from "@/lib/llm-api-presets";
import {
  DEFAULT_FAVORITE_HOME_INDEX_CODES,
  DEFAULT_HOME_INDEX_DISPLAY_FIELDS,
  HOME_INDEX_DISPLAY_FIELD_VALUES,
  getPlatformSettings,
  type HomeIndexDisplayField,
  type NewsSearchProviderId,
} from "@/lib/platform-settings-store";
import { Link } from "@/src/i18n/routing";

export default async function SettingsPage({
  params,
  searchParams = Promise.resolve({}),
}: {
  params: Promise<{ locale: string }>;
  searchParams?: Promise<{
    saved?: string;
    llm_error?: string;
    llm_preset?: string;
  }>;
}) {
  const { locale } = await params;
  const {
    saved,
    llm_error: llmError,
    llm_preset: requestedLlmPreset,
  } = await searchParams;
  const settings = await getPlatformSettings();
  const t = await getTranslations("Settings");
  const displayColorScheme =
    settings.color_scheme === "international"
      ? t("internationalConvention")
      : t("chinaConvention");
  const selectedHomeIndexDisplayFields = new Set(
    settings.home_index_display_fields,
  );
  const homeIndexDisplayFieldLabels: Record<HomeIndexDisplayField, string> = {
    latest_close: t("homeIndexFieldLatestClose"),
    percent_change: t("homeIndexFieldPercentChange"),
    freshness: t("homeIndexFieldFreshness"),
    as_of: t("homeIndexFieldAsOf"),
    region: t("homeIndexFieldRegion"),
    provider: t("homeIndexFieldProvider"),
  };
  const newsProviderReadinessLabels: Record<NewsSearchProviderId, string> = {
    anspire: t("newsProviderReadinessAnspire"),
    serpapi_baidu: t("newsProviderReadinessSerpApi"),
    tavily: t("newsProviderReadinessTavily"),
    bocha: t("newsProviderReadinessBocha"),
    brave: t("newsProviderReadinessBrave"),
    minimax: t("newsProviderReadinessMiniMax"),
    yfinance: t("newsProviderReadinessYfinance"),
    akshare: t("newsProviderReadinessAkshare"),
    tushare: t("newsProviderReadinessTushare"),
    mock: t("newsProviderReadinessMock"),
  };
  const newsProviderStatusLabel = (status: string) => {
    if (status === "implemented") return t("newsProviderStatusImplemented");
    if (status === "configured_only")
      return t("newsProviderStatusConfiguredOnly");
    if (status === "needs_contract")
      return t("newsProviderStatusNeedsContract");
    if (status === "existing") return t("newsProviderStatusExisting");
    if (status === "mock") return t("newsProviderStatusMock");
    return status;
  };
  const newsEnabledCount = settings.news_search_provider_capabilities.filter(
    (capability) => capability.enabled,
  ).length;
  const persistedLlmPreset = inferLlmApiPreset(settings);
  const llmPreset =
    llmError && requestedLlmPreset
      ? normalizeLlmApiPresetId(requestedLlmPreset)
      : persistedLlmPreset;
  const llmPresetLabels: Record<LlmApiPresetId, string> = {
    disabled: t("llmPresetDisabled"),
    deepseek: t("llmPresetDeepSeek"),
    openai: t("llmPresetOpenAI"),
    custom: t("llmPresetCustom"),
  };
  const llmErrorMessages: Record<LlmConfigErrorCode, string> = {
    invalid_base: t("llmErrorInvalidBase"),
    missing_model: t("llmErrorMissingModel"),
    missing_key: t("llmErrorMissingKey"),
  };
  const llmErrorMessage = Object.hasOwn(llmErrorMessages, llmError ?? "")
    ? llmErrorMessages[llmError as LlmConfigErrorCode]
    : null;
  const llmApiKeyHelp = settings.llm_api_key_configured
    ? t("llmApiKeyConfigured")
    : t("llmApiKeyRequired");

  return (
    <div className="space-y-6">
      {saved === "ok" ? (
        <FlashBanner variant="success" message={t("saveSuccess")} />
      ) : null}
      {saved === "error" ? (
        <FlashBanner variant="error" message={t("saveFailed")} />
      ) : null}

      <form action={savePlatformSettingsAction} className="space-y-4">
        <input type="hidden" name="locale" value={locale} />

        <FinancialPageHeader
          title={t("title")}
          description={t("description")}
          badges={[
            { label: t("displayPreferencesTitle"), variant: "secondary" },
            {
              label: t("activeProvider") + `: ${settings.market_data_provider}`,
            },
          ]}
          metrics={[
            {
              label: t("dataProviderTitle"),
              value: settings.market_data_provider,
              description: settings.market_data_provider_capabilities.find(
                (capability) =>
                  capability.provider === settings.market_data_provider,
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
              value: llmPresetLabels[llmPreset],
              description:
                llmPreset === "disabled"
                  ? t("llmDisabledStatus")
                  : settings.llm_api_key_configured
                    ? t("providerConfigured")
                    : t("providerNeedsSetup"),
            },
            {
              label: t("newsSourcesTitle"),
              value: newsEnabledCount,
              description: t("newsSourcesEnabledMetric"),
            },
            {
              label: t("homeIndexPreferencesTitle"),
              value: settings.favorite_home_index_codes.length,
              description: t("homeIndexCodesLabel"),
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
          <FinancialTerminalCard className="xl:col-span-2">
            <FinancialTerminalCardHeader>
              <CardTitle>{t("llmTitle")}</CardTitle>
              <CardDescription>{t("llmDesc")}</CardDescription>
            </FinancialTerminalCardHeader>
            <FinancialTerminalCardContent className="space-y-4">
              <LlmSettingsControl
                initialPreset={llmPreset}
                initialApiBase={settings.llm_api_base}
                initialModel={settings.llm_model}
                initialErrorCode={
                  llmError && Object.hasOwn(llmErrorMessages, llmError)
                    ? (llmError as LlmConfigErrorCode)
                    : null
                }
                initialErrorMessage={llmErrorMessage}
                labels={{
                  preset: t("llmPreset"),
                  presetHint: t("llmPresetHint"),
                  presetOptions: llmPresetLabels,
                  apiKey: t("llmApiKey"),
                  apiKeyPlaceholder: t("llmApiKeyPlaceholder"),
                  apiKeyHelp: llmApiKeyHelp,
                  apiBase: t("llmApiBase"),
                  apiBaseHint: t("llmApiBaseHint"),
                  apiBasePlaceholder: "https://api.example.com/v1",
                  model: t("llmModel"),
                  modelHint: t("llmModelHint"),
                  modelPlaceholder: "model-name",
                  testConnection: t("llmTestConnection"),
                  testing: t("llmTesting"),
                  testHint: t("llmTestHint"),
                  testConnected: t("llmTestConnected"),
                  testProvider: t("llmTestProvider"),
                  testModel: t("llmTestModel"),
                  testLatency: t("llmTestLatency"),
                  testErrors: {
                    provider_disabled: t("llmTestProviderDisabled"),
                    key_not_configured: t("llmTestKeyNotConfigured"),
                    invalid_configuration: t("llmTestInvalidConfiguration"),
                    provider_unavailable: t("llmTestProviderUnavailable"),
                    invalid_provider_response: t("llmTestInvalidResponse"),
                    request_failed: t("llmTestRequestFailed"),
                  },
                }}
              />
            </FinancialTerminalCardContent>
          </FinancialTerminalCard>

          <details className="xl:col-span-2 rounded-md border border-dashed border-border/80 bg-card/95 p-4">
            <summary className="cursor-pointer text-sm font-semibold text-foreground">
              {t("advancedSettingsSummary")}
            </summary>
            <div className="mt-4 grid gap-4 xl:grid-cols-2">
          <FinancialTerminalCard>
            <FinancialTerminalCardHeader>
              <CardTitle>{t("dataProviderTitle")}</CardTitle>
              <CardDescription>{t("dataProviderDesc")}</CardDescription>
            </FinancialTerminalCardHeader>
            <FinancialTerminalCardContent className="space-y-4">
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
                {t("activeProvider")}:{" "}
                <span className="font-medium text-foreground">
                  {settings.market_data_provider}
                </span>
              </p>
              <div className="grid gap-3 md:grid-cols-2">
                {settings.market_data_provider_capabilities.map(
                  (capability) => (
                    <FinancialTerminalSurface
                      key={capability.provider}
                      className="p-3 text-sm"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="font-medium">{capability.provider}</div>
                        <span
                          className={
                            capability.configured
                              ? "rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-400"
                              : "rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-xs font-medium text-amber-300"
                          }
                        >
                          {capability.configured
                            ? t("providerConfigured")
                            : t("providerNeedsSetup")}
                        </span>
                      </div>
                      <div className="mt-2 text-muted-foreground">
                        {capability.active ? `${t("providerActive")}. ` : ""}
                        {capability.supports_daily_bars
                          ? t("dailyBarsSupported")
                          : t("dailyBarsUnsupported")}{" "}
                        {capability.supports_realtime_quotes
                          ? t("realtimeQuotesSupported")
                          : t("realtimeQuotesUnsupported")}
                      </div>
                      <p className="mt-2 text-xs text-muted-foreground">
                        {capability.provider === "mock"
                          ? t("mockReadiness")
                          : null}
                        {capability.provider === "yfinance"
                          ? t("yfinanceReadiness")
                          : null}
                        {capability.provider === "akshare"
                          ? t("akshareReadiness")
                          : null}
                        {capability.provider === "tushare"
                          ? t("tushareReadiness")
                          : null}
                      </p>
                    </FinancialTerminalSurface>
                  ),
                )}
              </div>
            </FinancialTerminalCardContent>
          </FinancialTerminalCard>

          <FinancialTerminalCard>
            <FinancialTerminalCardHeader>
              <CardTitle>{t("akshareTitle")}</CardTitle>
              <CardDescription>{t("akshareDesc")}</CardDescription>
            </FinancialTerminalCardHeader>
            <FinancialTerminalCardContent>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  name="akshare_enabled"
                  defaultChecked={settings.akshare_enabled}
                  className="h-4 w-4 rounded border-gray-300"
                />
                <span className="text-sm">{t("akshareEnableLabel")}</span>
              </label>
              <p className="mt-2 text-xs text-muted-foreground">
                {t("akshareHint")}
              </p>
            </FinancialTerminalCardContent>
          </FinancialTerminalCard>

          <FinancialTerminalCard>
            <FinancialTerminalCardHeader>
              <CardTitle>{t("tushareTitle")}</CardTitle>
              <CardDescription>{t("tushareDesc")}</CardDescription>
            </FinancialTerminalCardHeader>
            <FinancialTerminalCardContent className="space-y-4">
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
                    settings.tushare_token_configured
                      ? t("tushareTokenConfigured")
                      : t("tushareTokenPlaceholder")
                  }
                />
              </div>
              <div className="space-y-2">
                <label
                  className="text-sm font-medium"
                  htmlFor="tushare_http_url"
                >
                  {t("tushareHttpUrl")}
                </label>
                <Input
                  id="tushare_http_url"
                  name="tushare_http_url"
                  defaultValue={settings.tushare_http_url}
                  placeholder="http://api.tushare.pro (optional)"
                />
              </div>
              <p className="text-xs text-muted-foreground">
                {t("tushareHint")}
              </p>
            </FinancialTerminalCardContent>
          </FinancialTerminalCard>

          <FinancialTerminalCard>
            <FinancialTerminalCardHeader>
              <CardTitle>{t("eastmoneyAccessTitle")}</CardTitle>
              <CardDescription>{t("eastmoneyAccessDesc")}</CardDescription>
            </FinancialTerminalCardHeader>
            <FinancialTerminalCardContent className="space-y-4">
              <div className="space-y-2"><label className="text-sm font-medium" htmlFor="eastmoney_proxy_url">{t("eastmoneyProxy")}</label><Input id="eastmoney_proxy_url" name="eastmoney_proxy_url" type="password" defaultValue="" placeholder={settings.eastmoney_proxy_url_configured ? t("secretConfigured") : "http://proxy:port"} /></div>
              <div className="space-y-2"><label className="text-sm font-medium" htmlFor="eastmoney_cookie">{t("eastmoneyCookie")}</label><Input id="eastmoney_cookie" name="eastmoney_cookie" type="password" defaultValue="" placeholder={settings.eastmoney_cookie_configured ? t("secretConfigured") : t("eastmoneyCookiePlaceholder")} /></div>
              <p className="text-xs text-muted-foreground">{t("eastmoneyAccessHint")}</p>
            </FinancialTerminalCardContent>
          </FinancialTerminalCard>

          <FinancialTerminalCard className="xl:col-span-2">
            <FinancialTerminalCardHeader>
              <CardTitle>{t("newsSourcesTitle")}</CardTitle>
              <CardDescription>{t("newsSourcesDesc")}</CardDescription>
            </FinancialTerminalCardHeader>
            <FinancialTerminalCardContent className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,0.55fr)]">
              <div className="space-y-4">
                <fieldset className="space-y-3">
                  <legend className="text-sm font-medium">
                    {t("newsSourcesEnabledLabel")}
                  </legend>
                  <div className="grid gap-3 md:grid-cols-2">
                    {settings.news_search_provider_capabilities.map(
                      (capability) => (
                        <label
                          key={capability.provider}
                          className="flex min-h-28 gap-3 rounded-md border border-border/70 bg-background/60 p-3 text-sm"
                        >
                          <input
                            type="checkbox"
                            name="news_search_enabled_providers"
                            value={capability.provider}
                            defaultChecked={capability.enabled}
                            className="mt-1 h-4 w-4 rounded border-gray-300"
                          />
                          <span className="min-w-0 flex-1 space-y-2">
                            <span className="flex flex-wrap items-center gap-2">
                              <span className="font-medium">
                                {capability.display_name}
                              </span>
                              <span className="rounded-full border px-2 py-0.5 text-xs text-muted-foreground">
                                {capability.provider}
                              </span>
                              <span
                                className={
                                  capability.configured
                                    ? "rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-400"
                                    : "rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-xs font-medium text-amber-300"
                                }
                              >
                                {capability.configured
                                  ? t("providerConfigured")
                                  : t("providerNeedsSetup")}
                              </span>
                              <span className="rounded-full border border-border/70 bg-muted/30 px-2 py-0.5 text-xs font-medium text-muted-foreground">
                                {newsProviderStatusLabel(
                                  capability.implementation_status,
                                )}
                              </span>
                            </span>
                            <span className="block text-xs text-muted-foreground">
                              {newsProviderReadinessLabels[capability.provider]}
                            </span>
                            <span className="block text-xs text-muted-foreground">
                              {t("newsSourcesCitationBoundary")}
                            </span>
                          </span>
                        </label>
                      ),
                    )}
                  </div>
                </fieldset>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <label
                      className="text-sm font-medium"
                      htmlFor="news_search_key_anspire"
                    >
                      {t("newsSourcesAnspireKey")}
                    </label>
                    <Input
                      id="news_search_key_anspire"
                      name="news_search_key_anspire"
                      type="password"
                      defaultValue=""
                      placeholder={
                        settings.news_search_provider_keys_configured.anspire
                          ? t("newsProviderKeyConfigured")
                          : t("newsProviderKeyPlaceholder")
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <label
                      className="text-sm font-medium"
                      htmlFor="news_search_key_serpapi_baidu"
                    >
                      {t("newsSourcesSerpApiKey")}
                    </label>
                    <Input
                      id="news_search_key_serpapi_baidu"
                      name="news_search_key_serpapi_baidu"
                      type="password"
                      defaultValue=""
                      placeholder={
                        settings.news_search_provider_keys_configured
                          .serpapi_baidu
                          ? t("newsProviderKeyConfigured")
                          : t("newsProviderKeyPlaceholder")
                      }
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="space-y-2">
                  <label
                    className="text-sm font-medium"
                    htmlFor="news_search_provider_order"
                  >
                    {t("newsSourcesOrderLabel")}
                  </label>
                  <textarea
                    id="news_search_provider_order"
                    name="news_search_provider_order"
                    defaultValue={settings.news_search_provider_order.join(
                      "\n",
                    )}
                    rows={10}
                    className="min-h-48 w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-sm"
                  />
                  <p className="text-xs text-muted-foreground">
                    {t("newsSourcesOrderHint")}
                  </p>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <label
                      className="text-sm font-medium"
                      htmlFor="news_search_max_results"
                    >
                      {t("newsSourcesMaxResults")}
                    </label>
                    <Input
                      id="news_search_max_results"
                      name="news_search_max_results"
                      type="number"
                      min={1}
                      max={20}
                      defaultValue={settings.news_search_max_results}
                    />
                  </div>
                  <div className="space-y-2">
                    <label
                      className="text-sm font-medium"
                      htmlFor="news_search_timeout_seconds"
                    >
                      {t("newsSourcesTimeoutSeconds")}
                    </label>
                    <Input
                      id="news_search_timeout_seconds"
                      name="news_search_timeout_seconds"
                      type="number"
                      min={1}
                      max={30}
                      step={0.5}
                      defaultValue={settings.news_search_timeout_seconds}
                    />
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  {t("newsSourcesQuotaHint")}
                </p>
              </div>
            </FinancialTerminalCardContent>
          </FinancialTerminalCard>

          <FinancialTerminalCard>
            <FinancialTerminalCardHeader>
              <CardTitle>{t("displayPreferencesTitle")}</CardTitle>
            </FinancialTerminalCardHeader>
            <FinancialTerminalCardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  {t("colorSchemeLabel")}
                </label>
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
                        (
                        <span className="text-green-600 font-medium">
                          {t("greenUp")}
                        </span>{" "}
                        /{" "}
                        <span className="text-red-600 font-medium">
                          {t("redDown")}
                        </span>
                        )
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
                      <span className="text-sm">
                        {t("internationalConvention")}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        (
                        <span className="text-red-600 font-medium">
                          {t("redUp")}
                        </span>{" "}
                        /{" "}
                        <span className="text-green-600 font-medium">
                          {t("greenDown")}
                        </span>
                        )
                      </span>
                    </div>
                  </label>
                </div>
              </div>
            </FinancialTerminalCardContent>
          </FinancialTerminalCard>

          <FinancialTerminalCard className="xl:col-span-2">
            <FinancialTerminalCardHeader>
              <CardTitle>{t("homeIndexPreferencesTitle")}</CardTitle>
              <CardDescription>{t("homeIndexPreferencesDesc")}</CardDescription>
            </FinancialTerminalCardHeader>
            <FinancialTerminalCardContent className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,0.7fr)]">
              <div className="space-y-3">
                <label
                  className="text-sm font-medium"
                  htmlFor="favorite_home_index_codes"
                >
                  {t("homeIndexCodesLabel")}
                </label>
                <textarea
                  id="favorite_home_index_codes"
                  name="favorite_home_index_codes"
                  defaultValue={settings.favorite_home_index_codes.join("\n")}
                  rows={8}
                  className="min-h-36 w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-sm"
                />
                <p className="text-xs text-muted-foreground">
                  {t("homeIndexCodesHint")}
                </p>
                <p className="text-xs text-muted-foreground">
                  {t("homeIndexCodesDefault", {
                    codes: DEFAULT_FAVORITE_HOME_INDEX_CODES.join(", "),
                  })}
                </p>
              </div>
              <fieldset className="space-y-3">
                <legend className="text-sm font-medium">
                  {t("homeIndexFieldsLabel")}
                </legend>
                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-1">
                  {HOME_INDEX_DISPLAY_FIELD_VALUES.map((field) => (
                    <label
                      key={field}
                      className="flex min-h-10 items-center gap-3 rounded-md border border-border/70 bg-background/60 px-3 py-2"
                    >
                      <input
                        type="checkbox"
                        name="home_index_display_fields"
                        value={field}
                        defaultChecked={selectedHomeIndexDisplayFields.has(
                          field,
                        )}
                        className="h-4 w-4 rounded border-gray-300"
                      />
                      <span className="text-sm">
                        {homeIndexDisplayFieldLabels[field]}
                      </span>
                    </label>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground">
                  {t("homeIndexFieldsHint")}
                </p>
                <p className="text-xs text-muted-foreground">
                  {t("homeIndexFieldsDefault", {
                    fields: DEFAULT_HOME_INDEX_DISPLAY_FIELDS.map(
                      (field) => homeIndexDisplayFieldLabels[field],
                    ).join(", "),
                  })}
                </p>
              </fieldset>
            </FinancialTerminalCardContent>
          </FinancialTerminalCard>

          <FinancialTerminalCard className="xl:col-span-2">
            <FinancialTerminalCardHeader>
              <CardTitle>{t("macroFavoritesTitle")}</CardTitle>
              <CardDescription>{t("macroFavoritesDesc")}</CardDescription>
            </FinancialTerminalCardHeader>
            <FinancialTerminalCardContent className="space-y-3">
              <label
                className="text-sm font-medium"
                htmlFor="favorite_macro_indicator_codes"
              >
                {t("macroFavoritesLabel")}
              </label>
              <textarea
                id="favorite_macro_indicator_codes"
                name="favorite_macro_indicator_codes"
                defaultValue={settings.favorite_macro_indicator_codes.join(
                  "\n",
                )}
                rows={8}
                className="min-h-36 w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-sm"
              />
              <p className="text-xs text-muted-foreground">
                {t("macroFavoritesHint")}
              </p>
              <p className="text-xs text-muted-foreground">
                {t("macroFavoritesDefault")}
              </p>
            </FinancialTerminalCardContent>
          </FinancialTerminalCard>

          <FinancialTerminalCard className="xl:col-span-2">
            <FinancialTerminalCardHeader>
              <CardTitle>{t("maintenanceLinksTitle")}</CardTitle>
              <CardDescription>{t("maintenanceLinksDesc")}</CardDescription>
            </FinancialTerminalCardHeader>
            <FinancialTerminalCardContent className="flex flex-wrap gap-2">
              <Button type="button" variant="outline" size="sm" asChild>
                <Link href="/evidence">{t("openEvidence")}</Link>
              </Button>
              <Button type="button" variant="outline" size="sm" asChild>
                <Link href="/task-runs">{t("openTaskRuns")}</Link>
              </Button>
            </FinancialTerminalCardContent>
          </FinancialTerminalCard>
            </div>
          </details>
        </div>

      </form>
    </div>
  );
}
