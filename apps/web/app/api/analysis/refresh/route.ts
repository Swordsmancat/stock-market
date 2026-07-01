const apiBaseUrl =
  process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function POST(request: Request) {
  const requestUrl = new URL(request.url);
  const upstreamUrl = new URL("/analysis/refresh", apiBaseUrl);

  for (const key of ["symbol", "market", "start", "end", "ma_window", "provider"]) {
    const value = requestUrl.searchParams.get(key);
    if (value !== null) {
      upstreamUrl.searchParams.set(key, value);
    }
  }

  const response = await fetch(upstreamUrl.toString(), {
    method: "POST",
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
