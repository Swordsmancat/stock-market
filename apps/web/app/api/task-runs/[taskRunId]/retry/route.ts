const apiBaseUrl =
  process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ taskRunId: string }> },
) {
  const { taskRunId } = await params;
  const upstreamUrl = new URL(`/task-runs/${taskRunId}/retry`, apiBaseUrl);

  const response = await fetch(upstreamUrl.toString(), {
    method: "POST",
    cache: "no-store",
  });
  const body = await response.text();

  return new Response(body, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
    },
  });
}
