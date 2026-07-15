import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, expect, it, vi } from "vitest";

import enMessages from "../messages/en.json";

const { refreshMock } = vi.hoisted(() => ({
  refreshMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: refreshMock }),
}));

import { InstrumentWatchlistForm } from "./instrument-watchlist-form";

afterEach(() => {
  cleanup();
  refreshMock.mockReset();
  vi.restoreAllMocks();
});

function renderForm(membership: "watched" | "not_watched" | "unavailable") {
  render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <InstrumentWatchlistForm
        symbol="AAPL"
        market="US"
        name="Apple Inc."
        membership={membership}
      />
    </NextIntlClientProvider>,
  );
}

it("adds an exact identity and refreshes the server state", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "created" }), { status: 201 }),
  );
  renderForm("not_watched");

  fireEvent.click(screen.getByRole("button", { name: "Add to Watchlist" }));

  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith("/api/watchlist/items", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        symbol: "AAPL",
        market: "US",
        name: "Apple Inc.",
      }),
    });
  });
  expect(await screen.findByRole("status")).toHaveTextContent(
    "Added to watchlist.",
  );
  expect(screen.getByRole("button", { name: "Remove from Watchlist" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(refreshMock).toHaveBeenCalledTimes(1);
});

it("removes an exact identity without navigating away", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "removed" }), { status: 200 }),
  );
  renderForm("watched");

  fireEvent.click(screen.getByRole("button", { name: "Remove from Watchlist" }));

  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/watchlist/items?symbol=AAPL&market=US",
      { method: "DELETE" },
    );
  });
  expect(await screen.findByRole("status")).toHaveTextContent(
    "Removed from watchlist.",
  );
  expect(refreshMock).toHaveBeenCalledTimes(1);
});

it("disables the action when membership is unavailable", () => {
  const fetchMock = vi.spyOn(globalThis, "fetch");
  renderForm("unavailable");

  expect(
    screen.getByRole("button", { name: "Watchlist status unavailable" }),
  ).toBeDisabled();
  expect(fetchMock).not.toHaveBeenCalled();
});

it("keeps the current state and announces mutation failures", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "failed" }), { status: 503 }),
  );
  renderForm("not_watched");

  fireEvent.click(screen.getByRole("button", { name: "Add to Watchlist" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Could not update the watchlist. Try again.",
  );
  expect(screen.getByRole("button", { name: "Add to Watchlist" })).toHaveAttribute(
    "aria-pressed",
    "false",
  );
  expect(refreshMock).not.toHaveBeenCalled();
});
