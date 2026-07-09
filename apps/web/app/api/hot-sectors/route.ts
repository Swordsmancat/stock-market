import { backendFetch } from "@/lib/backend-api";

type HotSectorsStatus = "ok" | "degraded" | "unavailable";
type HotSectorsDataMode = "live" | "delayed" | "demo" | "mock" | "none";

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
  const limit = normalizeHotSectorsLimit(searchParams.get("limit"));
  const backendSearchParams = new URLSearchParams({ limit: String(limit) });
  const provider = searchParams.get("provider")?.trim();
  if (provider) {
    backendSearchParams.set("provider", provider);
  }
  const sectorType = searchParams.get("sector_type")?.trim();
  if (sectorType) {
    backendSearchParams.set("sector_type", sectorType);
  }
  const window = searchParams.get("window")?.trim();
  if (window) {
    backendSearchParams.set("window", window);
  }

  try {
    const response = await backendFetch(`/sectors/hot?${backendSearchParams.toString()}`, {
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

function normalizeHotSectorsLimit(rawLimit: string | null): number {
  const parsedLimit = Number.parseInt(rawLimit ?? "5", 10);
  if (Number.isNaN(parsedLimit)) {
    return 5;
  }
  return Math.min(Math.max(parsedLimit, 1), 10);
}
