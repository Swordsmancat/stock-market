import { getBackendApiUrl } from "@/lib/backend-api";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ symbol: string }> },
) {
  const { symbol } = await params;
  const requestUrl = new URL(request.url);
  const upstreamUrl = new URL(
    `/news/${encodeURIComponent(symbol)}/refresh`,
    getBackendApiUrl(),
  );
  const market = requestUrl.searchParams.get("market");
  if (market !== null) {
    upstreamUrl.searchParams.set("market", market);
  }

  try {
    const response = await fetch(upstreamUrl.toString(), {
      method: "POST",
      cache: "no-store",
    });
    const body = await response.text();

    return new Response(body, {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") ?? "application/json",
        "cache-control": "no-store",
      },
    });
  } catch {
    return Response.json(
      { detail: "News refresh is temporarily unavailable" },
      { status: 502, headers: { "cache-control": "no-store" } },
    );
  }
}
