import { getBackendApiUrl } from "@/lib/backend-api";

export async function POST(request: Request) {
  const response = await fetch(
    new URL("/ingestion/a-share-evidence-backfills", getBackendApiUrl()),
    {
      method: "POST",
      cache: "no-store",
      headers: { "content-type": "application/json" },
      body: await request.text(),
    },
  );

  return proxyResponse(response);
}

function proxyResponse(response: Response) {
  return new Response(response.body, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
      "cache-control": "no-store",
    },
  });
}
