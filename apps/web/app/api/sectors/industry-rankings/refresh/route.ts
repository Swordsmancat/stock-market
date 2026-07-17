import { getBackendApiUrl } from "@/lib/backend-api";

export async function POST(request: Request) {
  const source = new URL(request.url);
  const target = new URL("/sectors/industry-rankings/refresh", getBackendApiUrl());
  target.search = source.search;
  const response = await fetch(target, { method: "POST", cache: "no-store" });
  return new Response(await response.text(), { status: response.status, headers: { "content-type": response.headers.get("content-type") ?? "application/json" } });
}
