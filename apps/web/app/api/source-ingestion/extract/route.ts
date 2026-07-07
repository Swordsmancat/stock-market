import { backendFetch } from "@/lib/backend-api";

export async function POST(request: Request): Promise<Response> {
  const requestBody = await request.text();
  const backendResponse = await backendFetch("/source-ingestion/extract", {
    method: "POST",
    headers: {
      "Content-Type": request.headers.get("content-type") ?? "application/json",
    },
    body: requestBody,
    cache: "no-store",
  });

  const responseBody = await backendResponse.text();
  const contentType = backendResponse.headers.get("content-type") ?? "application/json";
  return new Response(responseBody, {
    status: backendResponse.status,
    headers: {
      "content-type": contentType,
      "cache-control": "no-store",
    },
  });
}
