import { getBackendApiUrl } from "@/lib/backend-api";
import { preserveNoStoreResponse } from "@/lib/research-shortlist-outcomes";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ runId: string }> },
) {
  const { runId } = await params;
  const response = await fetch(
    new URL(
      `/research-shortlists/${encodeURIComponent(runId)}/outcomes/evaluate`,
      getBackendApiUrl(),
    ),
    {
      method: "POST",
      body: await request.text(),
      cache: "no-store",
      headers: {
        "content-type": request.headers.get("content-type") ?? "application/json",
      },
    },
  );

  return preserveNoStoreResponse(response);
}
