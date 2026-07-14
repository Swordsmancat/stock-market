import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { FormEvent } from "react";
import { afterEach, expect, it, vi } from "vitest";

import { LlmSettingsControl } from "./llm-settings-control";

const labels = {
  preset: "API preset",
  presetHint: "Preset hint",
  presetOptions: {
    disabled: "Disabled",
    deepseek: "DeepSeek",
    openai: "OpenAI",
    custom: "Custom",
  },
  apiKey: "API Key",
  apiKeyPlaceholder: "Paste key",
  apiKeyHelp: "Saved key help",
  apiBase: "API Base URL",
  apiBaseHint: "Base hint",
  apiBasePlaceholder: "https://api.example/v1",
  model: "Model",
  modelHint: "Model hint",
  modelPlaceholder: "model-name",
  testConnection: "Test connection",
  testing: "Testing...",
  testHint: "Tests saved settings only.",
  testConnected: "Connected",
  testProvider: "Provider",
  testModel: "Model",
  testLatency: "Latency",
  testErrors: {
    provider_disabled: "Provider disabled",
    key_not_configured: "Key missing",
    invalid_configuration: "Invalid configuration",
    provider_unavailable: "Provider unavailable",
    invalid_provider_response: "Invalid response",
    request_failed: "Request failed",
  },
};

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("shows custom fields only for the custom preset without testing automatically", () => {
  const fetchMock = vi.spyOn(globalThis, "fetch");
  render(
    <LlmSettingsControl
      initialPreset="deepseek"
      initialApiBase="https://api.deepseek.com/v1"
      initialModel="deepseek-chat"
      labels={labels}
    />,
  );

  expect(screen.queryByLabelText("API Base URL")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Model")).not.toBeInTheDocument();
  expect(fetchMock).not.toHaveBeenCalled();

  fireEvent.change(screen.getByLabelText("API preset"), { target: { value: "openai" } });
  expect(screen.queryByLabelText("API Base URL")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Model")).not.toBeInTheDocument();
  expect(fetchMock).not.toHaveBeenCalled();

  fireEvent.change(screen.getByLabelText("API preset"), { target: { value: "custom" } });
  expect(screen.getByLabelText("API Base URL")).toBeInTheDocument();
  expect(screen.getByLabelText("Model")).toBeInTheDocument();
  expect(fetchMock).not.toHaveBeenCalled();
});

it("does not test the connection when the parent settings form is saved", () => {
  const fetchMock = vi.spyOn(globalThis, "fetch");
  const submitMock = vi.fn((event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
  });

  render(
    <form onSubmit={submitMock}>
      <LlmSettingsControl
        initialPreset="deepseek"
        initialApiBase="https://api.deepseek.com/v1"
        initialModel="deepseek-chat"
        labels={labels}
      />
      <button type="submit">Save</button>
    </form>,
  );

  fireEvent.click(screen.getByRole("button", { name: "Save" }));

  expect(submitMock).toHaveBeenCalledTimes(1);
  expect(fetchMock).not.toHaveBeenCalled();
});

it("makes one request per click and renders only sanitized connection metadata", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        status: "ok",
        code: "connected",
        provider: "openai",
        model: "deepseek-chat",
        latency_ms: 321,
        answer: "must not render",
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );
  render(
    <LlmSettingsControl
      initialPreset="deepseek"
      initialApiBase="https://api.deepseek.com/v1"
      initialModel="deepseek-chat"
      labels={labels}
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Test connection" }));
  expect(screen.getByRole("button", { name: "Testing..." })).toBeDisabled();

  await waitFor(() => expect(screen.getByRole("status")).toBeInTheDocument());
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(fetchMock).toHaveBeenCalledWith("/api/settings/llm/test", {
    method: "POST",
    cache: "no-store",
  });
  expect(screen.getByText("Provider: openai")).toBeInTheDocument();
  expect(screen.getByText("Model: deepseek-chat")).toBeInTheDocument();
  expect(screen.getByText("Latency: 321 ms")).toBeInTheDocument();
  expect(screen.queryByText("must not render")).not.toBeInTheDocument();
});

it("maps provider failures to stable localized messages", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        status: "error",
        code: "provider_unavailable",
        message: "upstream body must not render",
      }),
      { status: 502 },
    ),
  );
  render(
    <LlmSettingsControl
      initialPreset="deepseek"
      initialApiBase="https://api.deepseek.com/v1"
      initialModel="deepseek-chat"
      labels={labels}
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Test connection" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Provider unavailable");
  expect(screen.queryByText("upstream body must not render")).not.toBeInTheDocument();
});
