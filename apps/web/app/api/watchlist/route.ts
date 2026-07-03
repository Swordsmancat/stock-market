import { backendFetch } from "@/lib/backend-api";

export async function GET(request: Request) {
  try {
    const response = await backendFetch("/watchlist", {
      cache: "no-store"
    });

    if (!response.ok) {
      return Response.json({ error: "Failed to fetch watchlist" }, { status: 500 });
    }

    const data = await response.json();
    return Response.json(data);
  } catch (error) {
    console.error("Watchlist API error:", error);
    return Response.json({ error: "Internal server error" }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    
    const response = await backendFetch("/watchlist/items", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      cache: "no-store"
    });

    if (!response.ok) {
      return Response.json({ error: "Failed to add to watchlist" }, { status: 500 });
    }

    const data = await response.json();
    return Response.json(data);
  } catch (error) {
    console.error("Watchlist POST error:", error);
    return Response.json({ error: "Internal server error" }, { status: 500 });
  }
}

export async function DELETE(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const symbol = searchParams.get("symbol");
    const market = searchParams.get("market");

    if (!symbol || !market) {
      return Response.json({ error: "Symbol and market are required" }, { status: 400 });
    }

    const response = await backendFetch(
      `/watchlist/items?symbol=${encodeURIComponent(symbol)}&market=${encodeURIComponent(market)}`,
      {
        method: "DELETE",
        cache: "no-store"
      }
    );

    if (!response.ok) {
      return Response.json({ error: "Failed to remove from watchlist" }, { status: 500 });
    }

    const data = await response.json();
    return Response.json(data);
  } catch (error) {
    console.error("Watchlist DELETE error:", error);
    return Response.json({ error: "Internal server error" }, { status: 500 });
  }
}
