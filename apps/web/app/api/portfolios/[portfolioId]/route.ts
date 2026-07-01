import { getBackendApiUrl } from "@/lib/backend-api";


type RouteContext = {
  params: Promise<{ portfolioId: string }>;
};

export async function GET(_request: Request, context: RouteContext) {
  const { portfolioId } = await context.params;
  const response = await fetch(new URL(`/portfolios/${portfolioId}`, getBackendApiUrl()).toString(), {
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

export async function PATCH(request: Request, context: RouteContext) {
  const { portfolioId } = await context.params;
  const upstreamUrl = new URL(`/portfolios/${portfolioId}`, getBackendApiUrl());
  const body = await request.text();

  const response = await fetch(upstreamUrl.toString(), {
    method: "PATCH",
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

export async function DELETE(_request: Request, context: RouteContext) {
  const { portfolioId } = await context.params;
  const response = await fetch(new URL(`/portfolios/${portfolioId}`, getBackendApiUrl()).toString(), {
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
