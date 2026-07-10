import { getBackendApiUrl } from "@/lib/backend-api";

export async function POST() {
  const response = await fetch(new URL("/ingestion/instrument-universe", getBackendApiUrl()), {
    method: "POST",
    cache: "no-store",
  });
  return new Response(await response.text(), {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
      "cache-control": "no-store",
    },
  });
}
