import { afterEach, expect, it, vi } from "vitest";
const { urlMock } = vi.hoisted(() => ({ urlMock: vi.fn(() => "http://api.test") }));
vi.mock("@/lib/backend-api", () => ({ getBackendApiUrl:urlMock }));
import { POST } from "./route";
afterEach(() => vi.restoreAllMocks());
it("proxies a bounded explicit calendar refresh", async () => {
  const fetchMock = vi.spyOn(globalThis,"fetch").mockResolvedValue(new Response(JSON.stringify({status:"ok",fetched:10}),{status:200,headers:{"content-type":"application/json"}}));
  const body = JSON.stringify({start:"2026-07-01",end:"2026-07-31",dry_run:false});
  const response = await POST(new Request("http://localhost/api/economic-calendar/refresh",{method:"POST",headers:{"content-type":"application/json"},body}));
  expect(fetchMock).toHaveBeenCalledWith(new URL("http://api.test/economic-calendar/refresh"), expect.objectContaining({method:"POST",body}));
  expect(response.status).toBe(200);
});
