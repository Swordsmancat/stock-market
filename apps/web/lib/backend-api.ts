const DEFAULT_BACKEND = "http://127.0.0.1:8001";

export function getBackendApiUrl(): string {
  return process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_BACKEND;
}

export async function backendFetch(path: string, init?: RequestInit): Promise<Response> {
  const url = `${getBackendApiUrl()}${path.startsWith("/") ? path : `/${path}`}`;
  return fetch(url, { cache: "no-store", ...init });
}

export async function getBackendCapabilities(): Promise<{
  ok: boolean;
  endpoints: string[];
  hasWatchlist: boolean;
  hasSettings: boolean;
  hasPortfolios: boolean;
}> {
  try {
    const response = await backendFetch("/openapi.json");
    if (!response.ok) {
      return { ok: false, endpoints: [], hasWatchlist: false, hasSettings: false, hasPortfolios: false };
    }
    const payload = (await response.json()) as { paths?: Record<string, unknown> };
    const endpoints = Object.keys(payload.paths ?? {});
    return {
      ok: true,
      endpoints,
      hasWatchlist: endpoints.includes("/watchlist"),
      hasSettings: endpoints.includes("/settings/platform"),
      hasPortfolios: endpoints.includes("/portfolios"),
    };
  } catch {
    return { ok: false, endpoints: [], hasWatchlist: false, hasSettings: false, hasPortfolios: false };
  }
}
