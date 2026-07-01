import { getBackendApiUrl } from "@/lib/backend-api";


type RouteContext = {
  params: Promise<{ portfolioId: string }>;
};

export async function POST(request: Request, context: RouteContext) {
  const { portfolioId } = await context.params;
  const upstreamUrl = new URL(`/portfolios/${portfolioId}/positions`, getBackendApiUrl());
  const body = await request.text();

  const response = await fetch(upstreamUrl.toString(), {
    method: "POST",
    body,
    cache: "no-store",
    headers: {
      "content-type": request.headers.get("content-type") ?? "application/json",
    },
  });
  const responseBody = await response.text();

  return new Response(responseBody, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
    },
  });
}

export async function DELETE(request: Request, context: RouteContext) {
  const { portfolioId } = await context.params;
  const requestUrl = new URL(request.url);
  const upstreamUrl = new URL(`/portfolios/${portfolioId}/positions`, getBackendApiUrl());

  for (const key of ["symbol", "market"]) {
    const value = requestUrl.searchParams.get(key);
    if (value !== null) {
      upstreamUrl.searchParams.set(key, value);
    }
  }

  const response = await fetch(upstreamUrl.toString(), {
    method: "DELETE",
    cache: "no-store",
  });
  const body = await response.text();

  return new Response(body, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
    },
  });
}
