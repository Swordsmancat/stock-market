import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, expect, it } from "vitest";

import enMessages from "../messages/en.json";
import { AiResearchDesk } from "./ai-research-desk";

afterEach(() => {
  cleanup();
});
function renderDesk() {
  render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <AiResearchDesk
        locale="en"
        provider="yfinance"
        watchlistItems={[]}
        followedItems={[]}
        recommendations={[]}
        recommendationDiagnostics={[]}
        macroIndicators={[]}
        overviewDiagnostics={[]}
      />
    </NextIntlClientProvider>,
  );
}

it("applies a shortlist snapshot only to its symbol and clears it on ordinary selection", async () => {
  renderDesk();

  fireEvent(
    window,
    new CustomEvent("stock-discovery:select-symbol", {
      detail: {
        symbol: "600519",
        researchSnapshotId: "12345678-1234-1234-1234-123456789abc",
      },
    }),
  );

  expect(
    await screen.findByText("Daily shortlist snapshot 12345678..."),
  ).toHaveAttribute(
    "data-research-snapshot-id",
    "12345678-1234-1234-1234-123456789abc",
  );

  fireEvent.change(screen.getByLabelText("Manual symbol"), {
    target: { value: "MSFT" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Add" }));

  await waitFor(() => {
    expect(
      screen.queryByText("Daily shortlist snapshot 12345678..."),
    ).not.toBeInTheDocument();
  });
  expect(screen.getAllByText("MSFT").length).toBeGreaterThan(0);

  fireEvent(
    window,
    new CustomEvent("stock-discovery:select-symbol", {
      detail: {
        symbol: "600519",
        researchSnapshotId: "12345678-1234-1234-1234-123456789abc",
      },
    }),
  );
  expect(
    await screen.findByText("Daily shortlist snapshot 12345678..."),
  ).toBeInTheDocument();

  fireEvent(
    window,
    new CustomEvent("stock-discovery:select-symbol", {
      detail: { symbol: "AAPL" },
    }),
  );
  await waitFor(() => {
    expect(
      screen.queryByText("Daily shortlist snapshot 12345678..."),
    ).not.toBeInTheDocument();
  });
});
