import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

const { routerRefreshMock } = vi.hoisted(() => ({
  routerRefreshMock: vi.fn(),
}));

const translationMessages: Record<string, string> = {
  generateReport: "Generate report",
  generating: "Generating...",
  generateSuccess: "Report generation started.",
  generateFailed: "Could not generate report.",
  generateFailedDetail: "Could not generate report: {reason}.",
  viewGeneratedReport: "View generated report",
  viewTaskRun: "View task run",
};

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: routerRefreshMock,
  }),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, values?: Record<string, string>) => {
    const template = translationMessages[key] ?? key;
    if (!values) {
      return template;
    }
    return Object.entries(values).reduce(
      (message, [name, value]) => message.replace(`{${name}}`, value),
      template,
    );
  },
}));

import { GenerateDailyReportButton } from "./generate-daily-report-button";

type DeferredResponse = {
  promise: Promise<Response>;
  resolve: (response: Response) => void;
};

function createDeferredResponse(): DeferredResponse {
  let resolveDeferredResponse: (response: Response) => void = () => undefined;
  const promise = new Promise<Response>((resolve) => {
    resolveDeferredResponse = resolve;
  });

  return {
    promise,
    resolve: resolveDeferredResponse,
  };
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  routerRefreshMock.mockReset();
});

it("posts to the encoded report generation proxy and refreshes after success", async () => {
  const deferredResponse = createDeferredResponse();
  const fetchMock = vi.spyOn(globalThis, "fetch").mockReturnValue(deferredResponse.promise);

  render(
    <GenerateDailyReportButton
      symbol="BRK/B"
      start="2026-01-01"
      end="2026-01-31"
    />,
  );

  expect(screen.getByRole("button", { name: "Generate report" })).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Generate report" }));

  expect(screen.getByRole("button", { name: "Generating..." })).toBeDisabled();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/reports/BRK%2FB/daily/generate?start=2026-01-01&end=2026-01-31",
    { method: "POST" },
  );

  deferredResponse.resolve(
    new Response(JSON.stringify({ id: "report-123", task_run_id: "task-123", status: "stored" }), {
      status: 202,
      headers: { "content-type": "application/json" },
    }),
  );

  expect(await screen.findByText("Report generation started.")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "View generated report" })).toHaveAttribute("href", "/reports/report-123");
  expect(screen.getByRole("link", { name: "View task run" })).toHaveAttribute("href", "/task-runs/task-123");
  expect(screen.getByRole("button", { name: "Generate report" })).not.toBeDisabled();
  expect(routerRefreshMock).toHaveBeenCalledOnce();
});

it("shows a failure message and does not refresh after failed generation", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "provider unavailable" }), {
      status: 503,
      headers: { "content-type": "application/json" },
    }),
  );

  render(
    <GenerateDailyReportButton
      symbol="AAPL"
      start="2026-01-01"
      end="2026-01-31"
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Generate report" }));

  expect(await screen.findByText("Could not generate report: provider unavailable.")).toBeInTheDocument();
  await waitFor(() => {
    expect(screen.getByRole("button", { name: "Generate report" })).not.toBeDisabled();
  });
  expect(routerRefreshMock).not.toHaveBeenCalled();
});
