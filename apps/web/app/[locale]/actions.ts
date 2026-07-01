"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { backendFetch } from "@/lib/backend-api";
import { getPlatformSettings, savePlatformSettings } from "@/lib/platform-settings-store";

async function readJsonSafe(response: Response): Promise<Record<string, unknown>> {
  try {
    return (await response.json()) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function flashRedirect(locale: string, params: Record<string, string>) {
  const query = new URLSearchParams(params).toString();
  redirect(`/${locale}?${query}`);
}

function pageRedirect(path: string, params: Record<string, string>) {
  const query = new URLSearchParams(params).toString();
  redirect(`${path}?${query}`);
}

export async function triggerIngestionAction(formData: FormData) {
  const locale = String(formData.get("locale") ?? "zh");
  const market = String(formData.get("market") ?? "US");
  const start = String(formData.get("start") ?? "");
  const end = String(formData.get("end") ?? "");
  const settings = await getPlatformSettings();
  const provider = String(formData.get("provider") ?? settings.market_data_provider);

  const params = new URLSearchParams({ market, start, end, provider });
  const response = await backendFetch(`/ingestion/mock-snapshot?${params.toString()}`, {
    method: "POST",
  });
  const body = await readJsonSafe(response);

  if (!response.ok) {
    flashRedirect(locale, { ingest: "error", msg: "ingestion failed" });
  }

  if (body.status === "dispatched" && body.task_run && typeof body.task_run === "object") {
    const taskRun = body.task_run as Record<string, unknown>;
    const result = (taskRun.result_json ?? {}) as Record<string, unknown>;
    flashRedirect(locale, {
      ingest: "ok",
      bars: String(result.bar_count ?? 0),
      market: String(result.market ?? market),
    });
  }

  flashRedirect(locale, {
    ingest: "ok",
    bars: String(body.bar_count ?? 0),
    market: String(body.market ?? market),
  });
}

export async function refreshAnalysisAction(formData: FormData) {
  const locale = String(formData.get("locale") ?? "zh");
  const symbol = String(formData.get("symbol") ?? "AAPL");
  const market = String(formData.get("market") ?? "US");
  const start = String(formData.get("start") ?? "");
  const end = String(formData.get("end") ?? "");
  const maWindow = String(formData.get("ma_window") ?? "3");
  const returnTo = String(formData.get("return_to") ?? "").trim();
  const settings = await getPlatformSettings();
  const provider = String(formData.get("provider") ?? settings.market_data_provider);

  const redirectWithFlash = (params: Record<string, string>) => {
    if (returnTo) {
      pageRedirect(returnTo, params);
    }
    flashRedirect(locale, params);
  };

  const params = new URLSearchParams({
    symbol,
    market,
    start,
    end,
    ma_window: maWindow,
    provider,
  });

  let response = await backendFetch(`/analysis/refresh?${params.toString()}`, { method: "POST" });
  if (response.status === 404) {
    response = await backendFetch(`/analysis/refresh-sync?${params.toString()}`, { method: "POST" });
  }

  if (response.status === 404) {
    const ingestParams = new URLSearchParams({ market, start, end, provider });
    const ingestResponse = await backendFetch(`/ingestion/mock-snapshot?${ingestParams.toString()}`, {
      method: "POST",
    });
    if (!ingestResponse.ok) {
      redirectWithFlash({ analysis: "error", msg: "ingestion failed" });
    }
    const reportResponse = await backendFetch(
      `/reports/${encodeURIComponent(symbol)}/stock?start=${start}&end=${end}`,
    );
    if (!reportResponse.ok) {
      redirectWithFlash({ analysis: "error", msg: "report failed" });
    }
    redirectWithFlash({ analysis: "ok", symbol });
  }

  const body = await readJsonSafe(response);
  if (!response.ok) {
    redirectWithFlash({ analysis: "error", msg: String(body.detail ?? "refresh failed") });
  }

  if (body.status === "dispatched" && body.task_run && typeof body.task_run === "object") {
    const taskRun = body.task_run as Record<string, unknown>;
    if (taskRun.status === "failed") {
      redirectWithFlash({
        analysis: "error",
        msg: String(taskRun.error_message ?? "task failed"),
      });
    }
  }

  if (returnTo) {
    revalidatePath(returnTo);
  }
  redirectWithFlash({ analysis: "ok", symbol: String(body.symbol ?? symbol) });
}

export async function generateDailyReportAction(formData: FormData) {
  const locale = String(formData.get("locale") ?? "zh");
  const symbol = String(formData.get("symbol") ?? "").trim().toUpperCase();
  const start = String(formData.get("start") ?? "");
  const end = String(formData.get("end") ?? "");
  const returnTo = String(formData.get("return_to") ?? `/${locale}/instruments/${encodeURIComponent(symbol)}`);

  const params = new URLSearchParams({ start, end });
  const response = await backendFetch(
    `/reports/${encodeURIComponent(symbol)}/daily/generate?${params.toString()}`,
    { method: "POST" },
  );

  revalidatePath(returnTo);
  if (!response.ok) {
    pageRedirect(returnTo, { report: "error" });
  }
  pageRedirect(returnTo, { report: "ok" });
}

export async function savePlatformSettingsAction(formData: FormData) {
  const locale = String(formData.get("locale") ?? "zh");
  try {
    await savePlatformSettings({
      market_data_provider: String(formData.get("market_data_provider") ?? "yfinance"),
      llm_provider: String(formData.get("llm_provider") ?? "mock"),
      llm_api_key: String(formData.get("llm_api_key") ?? ""),
      llm_api_base: String(formData.get("llm_api_base") ?? "https://api.openai.com/v1"),
      akshare_enabled: formData.get("akshare_enabled") === "on",
      tushare_token: String(formData.get("tushare_token") ?? ""),
    });
    revalidatePath(`/${locale}/settings`);
  } catch {
    pageRedirect(`/${locale}/settings`, { saved: "error" });
  }
  pageRedirect(`/${locale}/settings`, { saved: "ok" });
}

export async function searchInstrumentAction(formData: FormData) {
  const locale = String(formData.get("locale") ?? "zh");
  const symbol = String(formData.get("symbol") ?? "")
    .trim()
    .toUpperCase();
  if (!symbol) {
    redirect(`/${locale}`);
  }
  redirect(`/${locale}/instruments/${encodeURIComponent(symbol)}`);
}

export async function addWatchlistItemAction(formData: FormData) {
  const locale = String(formData.get("locale") ?? "zh");
  const symbol = String(formData.get("symbol") ?? "").trim().toUpperCase();
  const market = String(formData.get("market") ?? "").trim().toUpperCase();
  const name = String(formData.get("name") ?? "").trim();
  const priceAbove = String(formData.get("price_above") ?? "").trim();
  const rsiBelow = String(formData.get("rsi_below") ?? "").trim();

  if (!symbol || !market) {
    pageRedirect(`/${locale}/watchlist`, { op: "error", reason: "missing_fields" });
  }

  const alertRules: Record<string, number> = {};
  if (priceAbove) alertRules.price_above = Number(priceAbove);
  if (rsiBelow) alertRules.rsi_below = Number(rsiBelow);

  const response = await backendFetch("/watchlist/items", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      symbol,
      market,
      name: name || null,
      alert_rules: alertRules,
    }),
  });

  revalidatePath(`/${locale}/watchlist`);
  if (!response.ok) {
    const body = await readJsonSafe(response);
    pageRedirect(`/${locale}/watchlist`, {
      op: "error",
      reason: String(body.detail ?? `http_${response.status}`),
    });
  }
  pageRedirect(`/${locale}/watchlist`, { op: "added" });
}

export async function removeWatchlistItemAction(formData: FormData) {
  const locale = String(formData.get("locale") ?? "zh");
  const symbol = String(formData.get("symbol") ?? "");
  const market = String(formData.get("market") ?? "");
  const params = new URLSearchParams({ symbol, market });
  const response = await backendFetch(`/watchlist/items?${params.toString()}`, { method: "DELETE" });
  revalidatePath(`/${locale}/watchlist`);
  if (!response.ok) {
    pageRedirect(`/${locale}/watchlist`, { op: "error", reason: `http_${response.status}` });
  }
  pageRedirect(`/${locale}/watchlist`, { op: "removed" });
}

export async function updateWatchlistAlertsAction(formData: FormData) {
  const locale = String(formData.get("locale") ?? "zh");
  const symbol = String(formData.get("symbol") ?? "");
  const market = String(formData.get("market") ?? "");
  const name = String(formData.get("name") ?? "");
  const priceAbove = String(formData.get("price_above") ?? "").trim();
  const rsiBelow = String(formData.get("rsi_below") ?? "").trim();
  const alertRules: Record<string, number> = {};
  if (priceAbove) alertRules.price_above = Number(priceAbove);
  if (rsiBelow) alertRules.rsi_below = Number(rsiBelow);

  const response = await backendFetch("/watchlist/items", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ symbol, market, name, alert_rules: alertRules }),
  });
  revalidatePath(`/${locale}/watchlist`);
  if (!response.ok) {
    pageRedirect(`/${locale}/watchlist`, { op: "error", reason: `http_${response.status}` });
  }
  pageRedirect(`/${locale}/watchlist`, { op: "alerts_updated" });
}

export async function createPortfolioAction(formData: FormData) {
  const locale = String(formData.get("locale") ?? "zh");
  const name = String(formData.get("name") ?? "").trim();
  const baseCurrency = String(formData.get("base_currency") ?? "USD").trim().toUpperCase();

  if (!name) {
    pageRedirect(`/${locale}/portfolios`, { op: "error", reason: "missing_name" });
  }

  const response = await backendFetch("/portfolios", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ name, base_currency: baseCurrency }),
  });

  revalidatePath(`/${locale}/portfolios`);
  if (!response.ok) {
    pageRedirect(`/${locale}/portfolios`, { op: "error", reason: `http_${response.status}` });
  }

  const created = (await readJsonSafe(response)) as { id?: string };
  if (created.id) {
    pageRedirect(`/${locale}/portfolios`, { portfolio: created.id, op: "created" });
  }
  pageRedirect(`/${locale}/portfolios`, { op: "created" });
}

export async function addPortfolioPositionAction(formData: FormData) {
  const locale = String(formData.get("locale") ?? "zh");
  const portfolioId = String(formData.get("portfolio_id") ?? "");
  const symbol = String(formData.get("symbol") ?? "").trim().toUpperCase();
  const market = String(formData.get("market") ?? "").trim().toUpperCase();
  const name = String(formData.get("name") ?? "").trim();
  const quantity = Number(formData.get("quantity"));
  const avgCost = Number(formData.get("avg_cost"));

  if (!portfolioId || !symbol || !market || !Number.isFinite(quantity) || !Number.isFinite(avgCost)) {
    pageRedirect(`/${locale}/portfolios`, { portfolio: portfolioId, op: "error", reason: "missing_fields" });
  }

  const response = await backendFetch(`/portfolios/${portfolioId}/positions`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      symbol,
      market,
      name: name || null,
      quantity,
      avg_cost: avgCost,
    }),
  });

  revalidatePath(`/${locale}/portfolios`);
  if (!response.ok) {
    pageRedirect(`/${locale}/portfolios`, { portfolio: portfolioId, op: "error", reason: `http_${response.status}` });
  }
  pageRedirect(`/${locale}/portfolios`, { portfolio: portfolioId, op: "position_added" });
}

export async function removePortfolioPositionAction(formData: FormData) {
  const locale = String(formData.get("locale") ?? "zh");
  const portfolioId = String(formData.get("portfolio_id") ?? "");
  const symbol = String(formData.get("symbol") ?? "");
  const market = String(formData.get("market") ?? "");
  const params = new URLSearchParams({ symbol, market });
  const response = await backendFetch(`/portfolios/${portfolioId}/positions?${params.toString()}`, {
    method: "DELETE",
  });

  revalidatePath(`/${locale}/portfolios`);
  if (!response.ok) {
    pageRedirect(`/${locale}/portfolios`, { portfolio: portfolioId, op: "error", reason: `http_${response.status}` });
  }
  pageRedirect(`/${locale}/portfolios`, { portfolio: portfolioId, op: "position_removed" });
}

export async function renamePortfolioAction(formData: FormData) {
  const locale = String(formData.get("locale") ?? "zh");
  const portfolioId = String(formData.get("portfolio_id") ?? "");
  const name = String(formData.get("name") ?? "").trim();

  if (!portfolioId || !name) {
    pageRedirect(`/${locale}/portfolios`, { portfolio: portfolioId, op: "error", reason: "missing_name" });
  }

  const response = await backendFetch(`/portfolios/${portfolioId}`, {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ name }),
  });

  revalidatePath(`/${locale}/portfolios`);
  if (!response.ok) {
    pageRedirect(`/${locale}/portfolios`, { portfolio: portfolioId, op: "error", reason: `http_${response.status}` });
  }
  pageRedirect(`/${locale}/portfolios`, { portfolio: portfolioId, op: "renamed" });
}

export async function deletePortfolioAction(formData: FormData) {
  const locale = String(formData.get("locale") ?? "zh");
  const portfolioId = String(formData.get("portfolio_id") ?? "");
  const response = await backendFetch(`/portfolios/${portfolioId}`, { method: "DELETE" });

  revalidatePath(`/${locale}/portfolios`);
  if (!response.ok) {
    pageRedirect(`/${locale}/portfolios`, { op: "error", reason: `http_${response.status}` });
  }
  pageRedirect(`/${locale}/portfolios`, { portfolio: "demo", op: "deleted" });
}

export async function addInstrumentToWatchlistAction(formData: FormData) {
  const locale = String(formData.get("locale") ?? "zh");
  const symbol = String(formData.get("symbol") ?? "").trim().toUpperCase();
  const market = String(formData.get("market") ?? "").trim().toUpperCase();
  const name = String(formData.get("name") ?? "").trim();
  const returnTo = String(formData.get("return_to") ?? `/${locale}/instruments/${symbol}`);

  const response = await backendFetch("/watchlist/items", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ symbol, market, name: name || null, alert_rules: {} }),
  });

  revalidatePath(returnTo);
  if (!response.ok) {
    const body = await readJsonSafe(response);
    pageRedirect(returnTo, { watchlist: "error", reason: String(body.detail ?? `http_${response.status}`) });
  }
  pageRedirect(returnTo, { watchlist: "added" });
}
