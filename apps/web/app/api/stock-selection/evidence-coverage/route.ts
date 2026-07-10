import { getBackendApiUrl } from "@/lib/backend-api";

export async function GET() {
  const response = await fetch(
    new URL("/stock-selection/evidence-coverage?market=CN&provider=akshare", getBackendApiUrl()),
    { cache: "no-store" },
  );

  return new Response(await response.text(), {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
      "cache-control": "no-store",
    },
  });
}
