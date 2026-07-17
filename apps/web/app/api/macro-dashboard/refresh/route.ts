import { getBackendApiUrl } from "@/lib/backend-api";

export async function POST(request: Request) {
  const upstreamUrl = new URL(
    "/market-indicators/official-refresh/akshare-cn",
    getBackendApiUrl(),
  );
  const body = await request.text();
  const response = await fetch(upstreamUrl.toString(), {
    method: "POST",
    body,
    cache: "no-store",
    headers: {
      "content-type": request.headers.get("content-type") ?? "application/json",
    },
  });
  return new Response(await response.text(), {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
      "cache-control": "no-store",
    },
  });
}
