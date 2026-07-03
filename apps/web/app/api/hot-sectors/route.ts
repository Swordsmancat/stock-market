import { backendFetch } from "@/lib/backend-api";

type HotSectorsStatus = "ok" | "degraded" | "unavailable";
type HotSectorsDataMode = "live" | "demo" | "mock" | "none";

function unavailableHotSectorsPayload(message: string) {
  return {
    status: "unavailable" satisfies HotSectorsStatus,
    data_mode: "none" satisfies HotSectorsDataMode,
    source: "backend_proxy",
    message,
    count: 0,
    items: [],
  };
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const limit = searchParams.get("limit") || "5";

  try {
    const response = await backendFetch(`/sectors/hot?limit=${limit}`, {
      cache: "no-store"
    });

    if (!response.ok) {
      return Response.json(unavailableHotSectorsPayload("Failed to fetch hot sectors"), { status: 502 });
    }

    const data = await response.json();
    return Response.json(data);
  } catch (error) {
    console.error("Hot sectors API error:", error);
    return Response.json(unavailableHotSectorsPayload("Internal server error"), { status: 502 });
  }
}
