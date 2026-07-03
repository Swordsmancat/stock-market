import { fetchInstrumentDetailPayload, normalizeInstrumentDetailProvider } from "@/lib/instrument-detail";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ symbol: string }> }
) {
  const { symbol } = await params;
  const requestUrl = new URL(request.url);
  const providerName = normalizeInstrumentDetailProvider(requestUrl.searchParams.get("provider"));

  try {
    const result = await fetchInstrumentDetailPayload({ symbol, providerName });
    if (result.status === "failed") {
      return new Response(result.body, {
        status: result.responseStatus,
        headers: result.headers,
      });
    }
    return Response.json(result.payload);
  } catch (error) {
    console.error("Instrument detail API error:", error);
    return Response.json({ detail: "Instrument detail API error" }, { status: 502 });
  }
}
