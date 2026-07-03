import { backendFetch } from "@/lib/backend-api";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const symbols = searchParams.get("symbols") ?? "";
  const limit = searchParams.get("limit") ?? "5";

  if (symbols.trim().length === 0) {
    return Response.json(
      { status: "error", error: "symbols query parameter is required", items: [] },
      { status: 400 },
    );
  }

  try {
    const response = await backendFetch(
      `/recommendations?symbols=${encodeURIComponent(symbols)}&limit=${encodeURIComponent(limit)}`,
      { cache: "no-store" },
    );

    if (!response.ok) {
      return Response.json(
        { status: "error", error: "Failed to fetch recommendations", items: [] },
        { status: 500 },
      );
    }

    const payload = await response.json();
    return Response.json(payload);
  } catch (error) {
    console.error("Recommendations API error:", error);
    return Response.json(
      { status: "error", error: "Internal server error", items: [] },
      { status: 500 },
    );
  }
}
