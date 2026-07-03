import { InstrumentDetailClient } from "@/components/instrument-detail-client";

export default async function InstrumentDetailPage({
  params,
}: {
  params: Promise<{ locale: string; symbol: string }>;
}) {
  const { locale, symbol } = await params;

  return <InstrumentDetailClient symbol={symbol} locale={locale} />;
}
