import { getBackendApiUrl } from "@/lib/backend-api";

export async function GET(request: Request) {
  const requestUrl = new URL(request.url);
  const upstreamUrl = new URL("/market-daily-evidence", getBackendApiUrl());
  for (const [key, value] of requestUrl.searchParams.entries()) {
    upstreamUrl.searchParams.append(key, value);
  }

  const response = await fetch(upstreamUrl.toString(), {
    method: "GET",
    cache: "no-store",
  });
  const responseBody = await response.text();

  return new Response(responseBody, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
      "cache-control": "no-store",
    },
  });
}

export async function POST(request: Request) {
  const upstreamUrl = new URL("/market-daily-evidence/import", getBackendApiUrl());
  const body = await request.text();

  const response = await fetch(upstreamUrl.toString(), {
    method: "POST",
    body,
    cache: "no-store",
    headers: {
      "content-type": request.headers.get("content-type") ?? "application/json",
    },
  });
  const responseBody = await response.text();

  return new Response(responseBody, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
      "cache-control": "no-store",
    },
  });
}
