import { getBackendApiUrl } from "@/lib/backend-api";

export async function POST(request: Request) {
  const response = await fetch(new URL("/stock-selection/discover", getBackendApiUrl()), {
    method: "POST",
    body: await request.text(),
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
