import { getBackendApiUrl } from "@/lib/backend-api";


export async function POST(request: Request) {
  const requestUrl = new URL(request.url);
  const upstreamUrl = new URL("/ingestion/mock-snapshot", getBackendApiUrl());

  for (const key of ["market", "start", "end", "provider"]) {
    const value = requestUrl.searchParams.get(key);
    if (value !== null) {
      upstreamUrl.searchParams.set(key, value);
    }
  }

  const response = await fetch(upstreamUrl.toString(), {
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
