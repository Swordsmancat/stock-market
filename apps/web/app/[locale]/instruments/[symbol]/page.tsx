import { InstrumentDetailClient } from "@/components/instrument-detail-client";
import {
  fetchInstrumentDetailContext,
  fetchInstrumentDetailPayload,
  normalizeInstrumentDetailProvider,
} from "@/lib/instrument-detail";

export default async function InstrumentDetailPage({
  params,
  searchParams = Promise.resolve({}),
}: {
  params: Promise<{ locale: string; symbol: string }>;
  searchParams?: Promise<{
    provider?: string | string[];
    market?: string | string[];
    research_snapshot_id?: string | string[];
  }>;
}) {
  const { locale, symbol } = await params;
  const rawSearchParams = await searchParams;
  const provider = firstSearchParam(rawSearchParams.provider);
  const market = firstSearchParam(rawSearchParams.market);
  const researchSnapshotId = firstSearchParam(rawSearchParams.research_snapshot_id);
  const providerName = normalizeInstrumentDetailProvider(provider);
  const [detailResult, detailContext] = await Promise.all([
    fetchInstrumentDetailPayload({ symbol, providerName, market }),
    fetchInstrumentDetailContext(symbol, market),
  ]);
  const initialData = detailResult.status === "loaded" ? detailResult.payload : null;
  const initialError = detailResult.status === "failed" ? "Failed to fetch instrument data" : null;

  return (
    <InstrumentDetailClient
      symbol={symbol}
      locale={locale}
      initialData={initialData}
      initialError={initialError}
      detailContext={detailContext}
      researchSnapshotId={researchSnapshotId ?? null}
    />
  );
}

function firstSearchParam(value: string | string[] | undefined): string | undefined {
  const candidate = Array.isArray(value) ? value[0] : value;
  return candidate?.trim() || undefined;
}
