import { getBackendApiUrl } from "@/lib/backend-api";


export async function GET(
  _request: Request,
  context: { params: Promise<{ taskRunId: string }> },
) {
  const { taskRunId } = await context.params;
  const response = await fetch(`${getBackendApiUrl()}/task-runs/${taskRunId}`, { cache: "no-store" });
  const body = await response.text();

  return new Response(body, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
    },
  });
}
