import { getBackendApiUrl } from "@/lib/backend-api";


export async function POST(
  request: Request,
  context: { params: Promise<{ symbol: string }> },
) {
  const { symbol } = await context.params;
  const url = new URL(request.url);
  const upstream = new URL(`/reports/${encodeURIComponent(symbol)}/daily/generate`, getBackendApiUrl());
  url.searchParams.forEach((value, key) => {
    upstream.searchParams.set(key, value);
  });

  const response = await fetch(upstream.toString(), {
    method: "POST",
    cache: "no-store",
  });
  const body = await response.text();

  return new Response(body, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
    },
  });
}
