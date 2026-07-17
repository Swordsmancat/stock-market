import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import StorageOverviewPage from "./page";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const payload = {
  status: "ok",
  engine: "PostgreSQL",
  row_count_kind: "estimated",
  collected_at: "2026-07-17T10:00:00+00:00",
  summary: {
    table_count: 2,
    estimated_rows: 81_011,
    data_bytes: 49_650_000,
    index_bytes: 10_000,
    total_bytes: 49_660_000,
  },
  domains: [
    {
      code: "news_disclosures",
      table_count: 1,
      estimated_rows: 81_000,
      data_bytes: 49_650_000,
      index_bytes: 10_000,
      total_bytes: 49_660_000,
      tables: [
        {
          name: "news_articles",
          estimated_rows: 81_000,
          data_bytes: 49_650_000,
          index_bytes: 10_000,
          total_bytes: 49_660_000,
        },
      ],
    },
    {
      code: "research_outputs",
      table_count: 1,
      estimated_rows: 11,
      data_bytes: null,
      index_bytes: null,
      total_bytes: null,
      tables: [
        {
          name: "generated_reports",
          estimated_rows: 11,
          data_bytes: null,
          index_bytes: null,
          total_bytes: null,
        },
      ],
    },
  ],
};

it("renders a truthful read-only storage inventory", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(payload)),
  );

  render(
    await StorageOverviewPage({
      params: Promise.resolve({ locale: "en-US" }),
    }),
  );

  expect(screen.getByRole("heading", { name: "Data Storage" })).toBeInTheDocument();
  expect(screen.getAllByText("News and disclosures")).toHaveLength(2);
  expect(screen.getByText("news_articles")).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "Table inventory" })).toHaveAttribute(
    "tabindex",
    "0",
  );
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(
    "http://127.0.0.1:8000/storage/overview",
    expect.objectContaining({ cache: "no-store" }),
  );
});

it("keeps backend failure distinct from an empty database", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("", { status: 503 }));

  render(
    await StorageOverviewPage({
      params: Promise.resolve({ locale: "en-US" }),
    }),
  );

  expect(screen.getByText("Storage overview is unavailable")).toBeInTheDocument();
  expect(screen.queryByText("The database has no application tables yet.")).not.toBeInTheDocument();
});
