import { getBackendApiUrl } from "@/lib/backend-api";

export async function GET(request: Request) {
  const requestUrl = new URL(request.url);
  const upstreamUrl = new URL("/research-shortlists/latest", getBackendApiUrl());
  upstreamUrl.search = requestUrl.search;

  const response = await fetch(upstreamUrl, { cache: "no-store" });
  return new Response(await response.text(), {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
      "cache-control": "no-store",
    },
  });
}
