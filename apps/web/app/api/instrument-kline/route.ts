import { getBackendApiUrl } from "@/lib/backend-api";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const upstream = new URL("/instrument-kline", getBackendApiUrl());
  url.searchParams.forEach((value, key) => upstream.searchParams.set(key, value));

  const response = await fetch(upstream.toString(), { cache: "no-store" });
  return new Response(await response.text(), {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
    },
  });
}
