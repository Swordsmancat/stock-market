import { getBackendApiUrl } from "@/lib/backend-api";
import { preserveNoStoreResponse } from "@/lib/research-shortlist-outcomes";

export async function GET(request: Request) {
  const requestUrl = new URL(request.url);
  const upstreamUrl = new URL("/research-shortlists/tracking", getBackendApiUrl());
  upstreamUrl.search = requestUrl.search;

  const response = await fetch(upstreamUrl, { cache: "no-store" });
  return preserveNoStoreResponse(response);
}
