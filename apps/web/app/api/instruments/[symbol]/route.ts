import { backendFetch } from "@/lib/backend-api";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ symbol: string }> }
) {
  const { symbol } = await params;

  try {
    // 简化实现: 只获取bars数据
    const barsResponse = await backendFetch(
      `/market-data/${encodeURIComponent(symbol)}/bars?timeframe=1d&limit=90`,
      { cache: "no-store" }
    );

    if (!barsResponse.ok) {
      console.error(`Failed to fetch bars for ${symbol}: ${barsResponse.status}`);
      // 返回Mock数据以便页面能正常显示
      return Response.json({
        symbol,
        latest: { status: "ok", item: null },
        bars: { status: "ok", items: [] },
      });
    }

    const barsData = await barsResponse.json();

    return Response.json({
      symbol,
      latest: { status: "ok", item: null },
      bars: barsData,
    });
  } catch (error) {
    console.error("Instrument detail API error:", error);
    // 返回Mock数据而不是错误
    return Response.json({
      symbol,
      latest: { status: "ok", item: null },
      bars: { status: "ok", items: [] },
    });
  }
}
