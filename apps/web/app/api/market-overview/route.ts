import { backendFetch } from "@/lib/backend-api";

const noStoreHeaders = {
  "Cache-Control": "no-store",
};

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const provider = searchParams.get("provider") || "yfinance";

  try {
    const response = await backendFetch(
      `/dashboard/market-overview?provider=${encodeURIComponent(provider)}`,
      { cache: "no-store" }
    );

    if (!response.ok) {
      return Response.json(
        { error: "Failed to fetch market overview" },
        { status: 500, headers: noStoreHeaders },
      );
    }

    const data = await response.json();
    return Response.json(data, { headers: noStoreHeaders });
  } catch (error) {
    console.error("Market overview API error:", error);
    return Response.json(
      { error: "Internal server error" },
      { status: 500, headers: noStoreHeaders },
    );
  }
}
