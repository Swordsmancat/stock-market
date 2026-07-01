const apiBaseUrl =
  process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function GET(
  _request: Request,
  context: { params: Promise<{ taskRunId: string }> },
) {
  const { taskRunId } = await context.params;
  const response = await fetch(`${apiBaseUrl}/task-runs/${taskRunId}`, { cache: "no-store" });
  const body = await response.text();

  return new Response(body, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
    },
  });
}
