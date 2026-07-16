import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ComponentProps } from "react";
import { afterEach, expect, it } from "vitest";

import enMessages from "../messages/en.json";
import zhMessages from "../messages/zh.json";
import { AiResearchDesk } from "./ai-research-desk";

afterEach(() => {
  cleanup();
});
function renderDesk(
  overrides: Partial<ComponentProps<typeof AiResearchDesk>> = {},
  locale: "en" | "zh" = "en",
) {
  const messages = locale === "zh" ? zhMessages : enMessages;
  render(
    <NextIntlClientProvider locale={locale} messages={messages}>
      <AiResearchDesk
        locale={locale}
        provider="yfinance"
        watchlistItems={[]}
        followedItems={[]}
        recommendations={[]}
        recommendationDiagnostics={[]}
        macroIndicators={[]}
        overviewDiagnostics={[]}
        {...overrides}
      />
    </NextIntlClientProvider>,
  );
}

it("keeps source operations out of the default research question and visible flow", () => {
  renderDesk(
    {
      watchlistItems: [{ symbol: "000001", market: "CN", name: "平安银行" }],
      macroIndicators: [
        {
          code: "buffett_indicator_cn",
          name: "Buffett Indicator - China",
          region: "CN",
          status: "ok",
          value: 79.54,
          unit: "percent",
          as_of: "2025-12-31",
          source: "World Bank CM.MKT.LCAP.GD.ZS CHN",
        },
        {
          code: "us_10y_yield",
          name: "US 10Y Treasury Yield",
          region: "US",
          status: "no_data",
          value: null,
          no_data_reason: "No audited observation has been seeded yet.",
        },
        {
          code: "custom_macro",
          name: "自定义宏观指标",
          status: "no_data",
          value: null,
          no_data_reason: "Raw provider gap detail.",
        },
      ],
      officialSourceStatus: {
        status: "degraded",
        providers: [
          {
            provider: "fred",
            label: "FRED US macro",
            status: "needs_configuration",
            missing_indicator_codes: ["us_10y_yield"],
            recommended_next_action:
              "Set FRED_API_KEY, then run a dry-run refresh.",
          },
        ],
      },
      overviewDiagnostics: [
        {
          source: "market_indicators",
          code: "MACRO_INDICATOR_NO_DATA",
          status: "no_data",
          message: "Raw diagnostic detail.",
        },
      ],
    },
    "zh",
  );

  const question = screen.getByLabelText("你的问题");
  const questionValue = (question as HTMLTextAreaElement).value;
  expect(questionValue).toContain("中国巴菲特指标: 79.54%");
  expect(questionValue).not.toContain("US 10Y Treasury Yield");
  expect(questionValue).not.toContain("FRED US macro");
  expect(questionValue).not.toContain("FRED_API_KEY");
  expect(questionValue).not.toContain("No audited observation");

  expect(screen.getAllByText("中国巴菲特指标").length).toBeGreaterThan(0);
  expect(screen.queryByText("buffett_indicator_cn")).not.toBeInTheDocument();
  expect(screen.getByText("美国10年期国债收益率")).toBeInTheDocument();
  expect(screen.getByText("自定义宏观指标")).toBeInTheDocument();
  const macroContext = screen.getByTestId("ai-research-macro-context");
  expect(
    within(macroContext).queryByText(
      "No audited observation has been seeded yet.",
    ),
  ).not.toBeInTheDocument();
  expect(
    within(macroContext).queryByText("Raw provider gap detail."),
  ).not.toBeInTheDocument();

  const maintenance = screen
    .getByText("来源维护与诊断")
    .closest("details");
  expect(maintenance).not.toHaveAttribute("open");
  expect(within(maintenance as HTMLElement).getByText("FRED US macro")).toBeInTheDocument();
  expect(
    within(maintenance as HTMLElement).getByText(
      "No audited observation has been seeded yet.",
    ),
  ).not.toBeVisible();
  expect(within(maintenance as HTMLElement).getByText("Raw diagnostic detail.")).toBeInTheDocument();
});

it("localizes every built-in macro code in the bounded English cards", () => {
  const builtInIndicators = [
    ["buffett_indicator_us", "Buffett Indicator - United States"],
    ["buffett_indicator_cn", "Buffett Indicator - China"],
    ["buffett_indicator_hk", "Buffett Indicator - Hong Kong"],
    ["us_10y_yield", "US 10Y Treasury Yield"],
    ["us_2y_yield", "US 2Y Treasury Yield"],
    ["us_10y_2y_spread", "US 10Y-2Y Yield Spread"],
    ["us_cpi_yoy", "US CPI YoY"],
    ["cn_m2_yoy", "China M2 Money Supply YoY"],
    ["us_m2_yoy", "US M2 Money Supply YoY"],
  ] as const;
  const createIndicator = ([code, name]: (typeof builtInIndicators)[number]) => ({
    code,
    name: `Stored ${name}`,
    status: "ok",
    value: 1,
    as_of: "2025-12-31",
    source: "stored evidence",
  });

  renderDesk({ macroIndicators: builtInIndicators.slice(0, 8).map(createIndicator) });

  for (const [code, label] of builtInIndicators.slice(0, 8)) {
    expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    expect(screen.queryByText(code)).not.toBeInTheDocument();
  }

  cleanup();
  renderDesk({ macroIndicators: [createIndicator(builtInIndicators[8])] });

  expect(screen.getAllByText("US M2 Money Supply YoY").length).toBeGreaterThan(0);
  expect(screen.queryByText("us_m2_yoy")).not.toBeInTheDocument();
});

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
