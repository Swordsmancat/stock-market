import { backendFetch } from "@/lib/backend-api";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const limit = searchParams.get("limit") || "5";

  try {
    const response = await backendFetch(`/sectors/hot?limit=${limit}`, {
      cache: "no-store"
    });

    if (!response.ok) {
      return Response.json({ error: "Failed to fetch hot sectors" }, { status: 500 });
    }

    const data = await response.json();
    return Response.json(data);
  } catch (error) {
    console.error("Hot sectors API error:", error);
    return Response.json({ error: "Internal server error" }, { status: 500 });
  }
}
