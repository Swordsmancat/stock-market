import { getBackendApiUrl } from "@/lib/backend-api";

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ disclosureId: string }> },
) {
  const { disclosureId } = await params;
  const response = await fetch(
    new URL(`/official-disclosures/${encodeURIComponent(disclosureId)}/ingest-document`, getBackendApiUrl()),
    { method: "POST", cache: "no-store" },
  );
  return new Response(await response.text(), {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
      "cache-control": "no-store",
    },
  });
}
