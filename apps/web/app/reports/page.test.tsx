import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import ReportsPage from "./page";

afterEach(() => {
  vi.restoreAllMocks();
});

it("renders latest report, history, and citations", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.endsWith("/reports/AAPL/daily/latest")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "AAPL",
            as_of: "2026-01-20",
            content_markdown: "# AAPL 每日报告\n\n持久化日报：MA 119.00",
            citations: [
              "bars_1d:AAPL:2026-01-20",
              "news_articles:AAPL:https://example.com/aapl-services-growth",
            ],
          }),
        ),
      );
    }
    if (url.endsWith("/reports/AAPL/daily/history?limit=5")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            symbol: "AAPL",
            items: [
              { as_of: "2026-01-20", content_markdown: "# AAPL 每日报告\n\n最新日报" },
              { as_of: "2026-01-19", content_markdown: "# AAPL 每日报告\n\n上一交易日" },
            ],
          }),
        ),
      );
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });

  render(await ReportsPage());

  expect(screen.getByText("报告中心")).toBeInTheDocument();
  expect(screen.getByText("AAPL 最新日报")).toBeInTheDocument();
  expect(screen.getByText("报告日期：2026-01-20")).toBeInTheDocument();
  expect(
    screen.getByText((content) =>
      content.includes("# AAPL 每日报告") && content.includes("持久化日报：MA 119.00"),
    ),
  ).toBeInTheDocument();
  expect(screen.getByText("引用来源")).toBeInTheDocument();
  expect(screen.getByText("bars_1d:AAPL:2026-01-20")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "news_articles:AAPL:https://example.com/aapl-services-growth" }))
    .toHaveAttribute("href", "https://example.com/aapl-services-growth");
  expect(
    screen.getByText((content) => content.includes("2026-01-19") && content.includes("上一交易日")),
  ).toBeInTheDocument();
});
