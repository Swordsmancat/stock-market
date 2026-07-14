import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

const { pushMock } = vi.hoisted(() => ({
  pushMock: vi.fn(),
}));

vi.mock("@/src/i18n/routing", () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("@/app/[locale]/actions", () => ({
  searchInstrumentAction: vi.fn(),
}));

import { GlobalSearch } from "./global-search";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.useRealTimers();
  pushMock.mockReset();
});

it("waits for nonblank input and requests only a bounded result set", async () => {
  vi.useFakeTimers();
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        source: "database",
        items: [
          { symbol: "600519", name: "Kweichow Moutai", market: "CN" },
        ],
        total: 1,
        limit: 10,
        offset: 0,
        has_more: false,
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );

  render(<GlobalSearch />);
  fireEvent.click(screen.getByRole("button", { name: /Search stocks/ }));
  expect(fetchMock).not.toHaveBeenCalled();

  fireEvent.change(screen.getByPlaceholderText("Enter symbol, e.g. AAPL"), {
    target: { value: "600519" },
  });
  expect(fetchMock).not.toHaveBeenCalled();

  await act(async () => {
    await vi.advanceTimersByTimeAsync(250);
  });

  expect(fetchMock).toHaveBeenCalledOnce();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/instruments?q=600519&limit=10&offset=0",
  );
  expect(screen.getByText("Kweichow Moutai")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: /600519/ }));
  expect(pushMock).toHaveBeenCalledWith("/instruments/600519");
});

it("shows a localized failure without retrying the search", async () => {
  vi.useFakeTimers();
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValue(new Response(null, { status: 503 }));

  render(<GlobalSearch />);
  fireEvent.click(screen.getByRole("button", { name: /Search stocks/ }));
  fireEvent.change(screen.getByPlaceholderText("Enter symbol, e.g. AAPL"), {
    target: { value: "AAPL" },
  });

  await act(async () => {
    await vi.advanceTimersByTimeAsync(250);
  });

  expect(fetchMock).toHaveBeenCalledOnce();
  expect(
    screen.getByText("Could not load instruments. Check that the API is running."),
  ).toBeInTheDocument();
});
