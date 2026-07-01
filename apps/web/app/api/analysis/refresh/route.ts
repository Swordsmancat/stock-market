const apiBaseUrl =
  process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function buildUpstreamUrl(path: string, requestUrl: URL) {
  const upstreamUrl = new URL(path, apiBaseUrl);
  for (const key of ["symbol", "market", "start", "end", "ma_window", "provider"]) {
    const value = requestUrl.searchParams.get(key);
    if (value !== null) {
      upstreamUrl.searchParams.set(key, value);
    }
  }
  return upstreamUrl;
}

async function runLegacySyncAnalysis(requestUrl: URL): Promise<Response> {
  const symbol = requestUrl.searchParams.get("symbol");
  const market = requestUrl.searchParams.get("market");
  const start = requestUrl.searchParams.get("start");
  const end = requestUrl.searchParams.get("end");

  if (!symbol || !market || !start || !end) {
    return Response.json({ detail: "Missing analysis parameters" }, { status: 400 });
  }

  const ingestUrl = new URL("/ingestion/mock-snapshot", apiBaseUrl);
  ingestUrl.searchParams.set("market", market);
  ingestUrl.searchParams.set("start", start);
  ingestUrl.searchParams.set("end", end);

  const ingestResponse = await fetch(ingestUrl.toString(), {
    method: "POST",
    cache: "no-store",
  });
  if (!ingestResponse.ok) {
    const detail = await ingestResponse.text();
    return new Response(detail, {
      status: ingestResponse.status,
      headers: { "content-type": "application/json" },
    });
  }

  const reportUrl = new URL(`/reports/${encodeURIComponent(symbol)}/stock`, apiBaseUrl);
  reportUrl.searchParams.set("start", start);
  reportUrl.searchParams.set("end", end);
  const provider = requestUrl.searchParams.get("provider");
  if (provider) {
    reportUrl.searchParams.set("provider", provider);
  }

  const reportResponse = await fetch(reportUrl.toString(), { cache: "no-store" });
  if (!reportResponse.ok) {
    const detail = await reportResponse.text();
    return new Response(detail, {
      status: reportResponse.status,
      headers: { "content-type": "application/json" },
    });
  }

  return Response.json({
    symbol,
    market,
    status: "refreshed",
    ingestion: await ingestResponse.json(),
    report: await reportResponse.json(),
  });
}

export async function POST(request: Request) {
  const requestUrl = new URL(request.url);
  const asyncUrl = buildUpstreamUrl("/analysis/refresh", requestUrl);
  let response = await fetch(asyncUrl.toString(), {
    method: "POST",
    cache: "no-store",
  });

  if (response.status === 404) {
    const syncUrl = buildUpstreamUrl("/analysis/refresh-sync", requestUrl);
    response = await fetch(syncUrl.toString(), {
      method: "POST",
      cache: "no-store",
    });
  }

  if (response.status === 404) {
    return runLegacySyncAnalysis(requestUrl);
  }

  const body = await response.text();
  return new Response(body, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
    },
  });
}
