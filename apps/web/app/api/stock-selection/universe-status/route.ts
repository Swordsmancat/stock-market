import { getBackendApiUrl } from "@/lib/backend-api";

export async function GET(request: Request) {
  const requestUrl = new URL(request.url);
  const upstreamUrl = new URL("/stock-selection/universe-status", getBackendApiUrl());
  for (const [key, value] of requestUrl.searchParams.entries()) {
    upstreamUrl.searchParams.append(key, value);
  }
  const response = await fetch(upstreamUrl, { cache: "no-store" });
  return new Response(await response.text(), {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
      "cache-control": "no-store",
    },
  });
}
