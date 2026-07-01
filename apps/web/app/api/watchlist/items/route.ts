const apiBaseUrl =
  process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function POST(request: Request) {
  const upstreamUrl = new URL("/watchlist/items", apiBaseUrl);
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

export async function DELETE(request: Request) {
  const requestUrl = new URL(request.url);
  const upstreamUrl = new URL("/watchlist/items", apiBaseUrl);

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
