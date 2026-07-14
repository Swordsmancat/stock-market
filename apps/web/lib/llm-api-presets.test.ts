import { expect, it } from "vitest";

import {
  DEEPSEEK_API_BASE,
  DEEPSEEK_MODEL,
  OPENAI_API_BASE,
  OPENAI_MODEL,
  inferLlmApiPreset,
  isValidLlmApiBase,
  normalizeLlmModel,
  resolveLlmApiPreset,
} from "./llm-api-presets";

it("resolves built-in LLM API presets to compatible provider settings", () => {
  expect(resolveLlmApiPreset("deepseek", "ignored", "ignored")).toEqual({
    ok: true,
    settings: {
      llm_provider: "openai",
      llm_api_base: DEEPSEEK_API_BASE,
      llm_model: DEEPSEEK_MODEL,
    },
  });
  expect(resolveLlmApiPreset("openai", "ignored", "ignored")).toEqual({
    ok: true,
    settings: {
      llm_provider: "openai",
      llm_api_base: OPENAI_API_BASE,
      llm_model: OPENAI_MODEL,
    },
  });
  expect(
    resolveLlmApiPreset(
      "disabled",
      "not-a-url",
      " ",
    ),
  ).toEqual({
    ok: true,
    settings: {
      llm_provider: "mock",
      llm_api_base: OPENAI_API_BASE,
      llm_model: OPENAI_MODEL,
    },
  });
});

it("normalizes and validates custom OpenAI-compatible settings", () => {
  expect(
    resolveLlmApiPreset(
      "custom",
      " https://llm.example.test/v1/ ",
      " custom-model ",
    ),
  ).toEqual({
    ok: true,
    settings: {
      llm_provider: "openai",
      llm_api_base: "https://llm.example.test/v1",
      llm_model: "custom-model",
    },
  });
  expect(
    resolveLlmApiPreset("custom", "file:///tmp/model", "custom-model"),
  ).toEqual({ ok: false, error: "invalid_base" });
  expect(
    resolveLlmApiPreset("custom", "https://llm.example.test/v1", "  "),
  ).toEqual({ ok: false, error: "missing_model" });
  expect(isValidLlmApiBase("http://localhost:11434/v1/")).toBe(true);
  expect(isValidLlmApiBase("/v1/chat/completions")).toBe(false);
  expect(isValidLlmApiBase("https://user:secret@llm.example.test/v1")).toBe(
    false,
  );
  expect(isValidLlmApiBase("https://llm.example.test/v1?key=secret")).toBe(
    false,
  );
  expect(isValidLlmApiBase("https://llm.example.test:bad/v1")).toBe(false);
  expect(isValidLlmApiBase("https://llm.example.test/v1?")).toBe(false);
  expect(isValidLlmApiBase("https://exa mple.test/v1")).toBe(false);
  expect(isValidLlmApiBase("https:\\example.test\\v1")).toBe(false);
  expect(isValidLlmApiBase("https://%zz/v1")).toBe(false);
  expect(isValidLlmApiBase("https://%2F/v1")).toBe(false);
  expect(isValidLlmApiBase("https:example.test/v1")).toBe(false);
  expect(isValidLlmApiBase("http:///example.test/v1")).toBe(false);
  expect(isValidLlmApiBase("https://exa^mple.test/v1")).toBe(false);
  expect(isValidLlmApiBase("https://exa|mple.test/v1")).toBe(false);
  expect(isValidLlmApiBase("https://[v1.fe80::]/v1")).toBe(false);
  expect(normalizeLlmModel("  deepseek-chat  ")).toBe("deepseek-chat");
});

it("infers presets only when both the endpoint and model match", () => {
  expect(
    inferLlmApiPreset({
      llm_provider: "openai",
      llm_api_base: `${DEEPSEEK_API_BASE}/`,
      llm_model: DEEPSEEK_MODEL,
    }),
  ).toBe("deepseek");
  expect(
    inferLlmApiPreset({
      llm_provider: "openai",
      llm_api_base: DEEPSEEK_API_BASE,
      llm_model: OPENAI_MODEL,
    }),
  ).toBe("custom");
  expect(
    inferLlmApiPreset({
      llm_provider: "openai",
      llm_api_base: "https://llm.example.test/v1",
      llm_model: "custom-model",
    }),
  ).toBe("custom");
});
