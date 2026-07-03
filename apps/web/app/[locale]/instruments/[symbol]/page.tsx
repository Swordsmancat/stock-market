import { InstrumentDetailClient } from "@/components/instrument-detail-client";
import { fetchInstrumentDetailPayload, normalizeInstrumentDetailProvider } from "@/lib/instrument-detail";

export default async function InstrumentDetailPage({
  params,
  searchParams = Promise.resolve({}),
}: {
  params: Promise<{ locale: string; symbol: string }>;
  searchParams?: Promise<{ provider?: string }>;
}) {
  const { locale, symbol } = await params;
  const { provider } = await searchParams;
  const providerName = normalizeInstrumentDetailProvider(provider);
  const detailResult = await fetchInstrumentDetailPayload({ symbol, providerName });
  const initialData = detailResult.status === "loaded" ? detailResult.payload : null;
  const initialError = detailResult.status === "failed" ? "Failed to fetch instrument data" : null;

  return <InstrumentDetailClient symbol={symbol} locale={locale} initialData={initialData} initialError={initialError} />;
}
