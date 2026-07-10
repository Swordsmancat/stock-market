import { getBackendApiUrl } from "@/lib/backend-api";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ runId: string }> },
) {
  const { runId } = await params;
  const response = await fetch(
    new URL(`/ingestion/a-share-evidence-backfills/${encodeURIComponent(runId)}`, getBackendApiUrl()),
    { cache: "no-store" },
  );

  return new Response(response.body, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
      "cache-control": "no-store",
    },
  });
}
