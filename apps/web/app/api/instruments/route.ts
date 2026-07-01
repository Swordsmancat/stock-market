const apiBaseUrl =
  process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const upstream = new URL("/instruments", apiBaseUrl);
  url.searchParams.forEach((value, key) => {
    upstream.searchParams.set(key, value);
  });

  const response = await fetch(upstream.toString(), { cache: "no-store" });
  const body = await response.text();

  return new Response(body, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
    },
  });
}
