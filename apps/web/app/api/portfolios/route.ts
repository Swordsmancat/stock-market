import { getBackendApiUrl } from "@/lib/backend-api";


export async function GET() {
  const response = await fetch(new URL("/portfolios", getBackendApiUrl()).toString(), {
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

export async function POST(request: Request) {
  const upstreamUrl = new URL("/portfolios", getBackendApiUrl());
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
