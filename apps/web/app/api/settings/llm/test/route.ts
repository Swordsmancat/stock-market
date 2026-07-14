import { getBackendApiUrl } from "@/lib/backend-api";

export async function POST() {
  try {
    const response = await fetch(new URL("/settings/llm/test", getBackendApiUrl()), {
      method: "POST",
      cache: "no-store",
      headers: { "content-type": "application/json" },
    });
    return new Response(await response.text(), {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") ?? "application/json",
        "cache-control": "no-store",
      },
    });
  } catch {
    return Response.json(
      {
        status: "error",
        code: "provider_unavailable",
        message: "LLM provider is unavailable.",
      },
      { status: 502, headers: { "cache-control": "no-store" } },
    );
  }
}
