import { afterEach, expect, it, vi } from "vitest";

const { mkdirMock, readFileMock, writeFileMock } = vi.hoisted(() => ({
  mkdirMock: vi.fn(),
  readFileMock: vi.fn(),
  writeFileMock: vi.fn(),
}));

vi.mock("node:fs/promises", async (importOriginal) => {
  const actual = await importOriginal<typeof import("node:fs/promises")>();
  return {
    ...actual,
    default: {
      ...(actual as { default?: object }).default,
      mkdir: mkdirMock,
      readFile: readFileMock,
      writeFile: writeFileMock,
    },
    mkdir: mkdirMock,
    readFile: readFileMock,
    writeFile: writeFileMock,
  };
});

import {
  DEFAULT_FAVORITE_HOME_INDEX_CODES,
  DEFAULT_HOME_INDEX_DISPLAY_FIELDS,
  DEFAULT_NEWS_SEARCH_PROVIDER_ORDER,
  getPlatformSettings,
  normalizeFavoriteHomeIndexCodes,
  normalizeHomeIndexDisplayFields,
  normalizeNewsSearchEnabledProviders,
  normalizeNewsSearchProviderOrder,
  savePlatformSettings,
} from "./platform-settings-store";

afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllEnvs();
  vi.resetModules();
});

it("normalizes homepage index codes from strings while preserving order", () => {
  expect(normalizeFavoriteHomeIndexCodes("us_sp_500\ncn_csi_300, us_sp_500\n\ncn_chinext")).toEqual([
    "us_sp_500",
    "cn_csi_300",
    "cn_chinext",
  ]);
});

it("falls back to default homepage index codes when the input is empty", () => {
  expect(normalizeFavoriteHomeIndexCodes(" \n , ")).toEqual([...DEFAULT_FAVORITE_HOME_INDEX_CODES]);
  expect(normalizeFavoriteHomeIndexCodes(null)).toEqual([...DEFAULT_FAVORITE_HOME_INDEX_CODES]);
});

it("normalizes homepage index display fields and removes unknown values", () => {
  expect(
    normalizeHomeIndexDisplayFields([
      "latest_close",
      "provider",
      "unknown_field",
      "latest_close",
      "as_of",
    ]),
  ).toEqual(["latest_close", "provider", "as_of"]);
});

it("falls back to default homepage index display fields when no valid fields remain", () => {
  expect(normalizeHomeIndexDisplayFields("unknown_field, another_unknown")).toEqual([
    ...DEFAULT_HOME_INDEX_DISPLAY_FIELDS,
  ]);
});

it("normalizes news search provider order and appends registry providers", () => {
  expect(normalizeNewsSearchProviderOrder("serpapi_baidu\nanspire\nunknown\nanspire").slice(0, 3)).toEqual([
    "serpapi_baidu",
    "anspire",
    "tavily",
  ]);
  expect(normalizeNewsSearchProviderOrder(null)).toEqual([...DEFAULT_NEWS_SEARCH_PROVIDER_ORDER]);
});

it("normalizes enabled news search providers without forcing defaults for empty input", () => {
  expect(normalizeNewsSearchEnabledProviders(["anspire", "mock", "unknown", "anspire"])).toEqual([
    "anspire",
    "mock",
  ]);
  expect(normalizeNewsSearchEnabledProviders("")).toEqual([]);
});

it("keeps legacy model defaults consistent and never exposes a stored LLM key", async () => {
  readFileMock.mockResolvedValue(
    JSON.stringify({
      llm_provider: "openai",
      llm_api_key: "stored-secret",
      llm_api_base: "https://api.deepseek.com/v1/",
    }),
  );

  const settings = await getPlatformSettings();

  expect(settings.llm_api_base).toBe("https://api.deepseek.com/v1");
  expect(settings.llm_model).toBe("gpt-4o-mini");
  expect(settings.llm_api_key).toBe("");
  expect(settings.llm_api_key_configured).toBe(true);
});

it("uses configured environment defaults for blank legacy LLM fields", async () => {
  vi.stubEnv("LLM_PROVIDER", "openai");
  vi.stubEnv("LLM_API_BASE", "https://env-llm.example.test/v1");
  vi.stubEnv("LLM_MODEL", "env-model");
  vi.resetModules();
  readFileMock.mockResolvedValue(
    JSON.stringify({
      llm_provider: "openai",
      llm_api_key: "stored-secret",
      llm_api_base: " ",
      llm_model: " ",
    }),
  );
  const { getPlatformSettings: getSettingsWithEnv } = await import(
    "./platform-settings-store"
  );

  const settings = await getSettingsWithEnv();

  expect(settings.llm_provider).toBe("openai");
  expect(settings.llm_api_base).toBe("https://env-llm.example.test/v1");
  expect(settings.llm_model).toBe("env-model");
  expect(settings.llm_api_key_configured).toBe(true);
});

it("fails closed from a credential-bearing legacy API base before public projection", async () => {
  readFileMock.mockResolvedValue(
    JSON.stringify({
      llm_provider: "openai",
      llm_api_key: "stored-secret",
      llm_api_base: "https://user:base-secret@llm.example.test/v1",
      llm_model: "custom-model",
    }),
  );

  const settings = await getPlatformSettings();

  expect(settings.llm_api_base).toBe("https://api.openai.com/v1");
  expect(settings.llm_provider).toBe("mock");
  expect(settings.llm_api_key_configured).toBe(false);
  expect(JSON.stringify(settings)).not.toContain("base-secret");
});

it("falls back safely for non-object files and malformed LLM fields", async () => {
  readFileMock.mockResolvedValueOnce("null");
  expect(await getPlatformSettings()).toMatchObject({
    llm_provider: "mock",
    llm_api_base: "https://api.openai.com/v1",
    llm_model: "gpt-4o-mini",
    llm_api_key: "",
    llm_api_key_configured: false,
  });

  readFileMock.mockResolvedValueOnce(
    JSON.stringify({
      llm_provider: { value: "openai" },
      llm_api_key: { value: "must-not-be-used" },
      llm_api_base: 123,
      llm_model: [],
    }),
  );
  const malformed = await getPlatformSettings();
  expect(malformed).toMatchObject({
    llm_provider: "mock",
    llm_api_base: "https://api.openai.com/v1",
    llm_model: "gpt-4o-mini",
    llm_api_key: "",
    llm_api_key_configured: false,
  });
  expect(JSON.stringify(malformed)).not.toContain("must-not-be-used");
});

it.each([false, 0, [], {}])(
  "fails closed for an explicit non-string stored API base: %j",
  async (llmApiBase) => {
    readFileMock.mockResolvedValueOnce(
      JSON.stringify({
        llm_provider: "openai",
        llm_api_key: "custom-service-secret",
        llm_api_base: llmApiBase,
      }),
    );

    const settings = await getPlatformSettings();

    expect(settings.llm_provider).toBe("mock");
    expect(settings.llm_api_base).toBe("https://api.openai.com/v1");
    expect(settings.llm_api_key_configured).toBe(false);
    expect(JSON.stringify(settings)).not.toContain("custom-service-secret");
  },
);

it("preserves a blank-updated key and round-trips the configured model", async () => {
  readFileMock.mockResolvedValue(
    JSON.stringify({
      llm_provider: "openai",
      llm_api_key: "stored-secret",
      llm_api_base: "https://api.deepseek.com/v1",
      llm_model: "gpt-4o-mini",
    }),
  );

  const publicSettings = await savePlatformSettings({
    llm_api_key: "",
    llm_api_base: " https://api.deepseek.com/v1/ ",
    llm_model: " deepseek-chat ",
  });

  const written = JSON.parse(String(writeFileMock.mock.calls[0]?.[1]));
  expect(written.llm_api_key).toBe("stored-secret");
  expect(written.llm_api_base).toBe("https://api.deepseek.com/v1");
  expect(written.llm_model).toBe("deepseek-chat");
  expect(publicSettings.llm_api_key).toBe("");
  expect(publicSettings.llm_api_key_configured).toBe(true);
  expect(mkdirMock).toHaveBeenCalledOnce();
});

it("replaces a non-blank key without exposing it in the saved response", async () => {
  readFileMock.mockResolvedValue(
    JSON.stringify({
      llm_provider: "openai",
      llm_api_key: "stored-secret",
      llm_api_base: "https://api.openai.com/v1",
      llm_model: "gpt-4o-mini",
    }),
  );

  const publicSettings = await savePlatformSettings({
    llm_api_key: "replacement-secret",
  });

  const written = JSON.parse(String(writeFileMock.mock.calls[0]?.[1]));
  expect(written.llm_api_key).toBe("replacement-secret");
  expect(publicSettings.llm_api_key).toBe("");
  expect(publicSettings.llm_api_key_configured).toBe(true);
  expect(JSON.stringify(publicSettings)).not.toContain("replacement-secret");
});

it("clears the old key when a direct update changes the API host without a replacement", async () => {
  readFileMock.mockResolvedValue(
    JSON.stringify({
      llm_provider: "openai",
      llm_api_key: "deepseek-secret",
      llm_api_base: "https://api.deepseek.com/v1",
      llm_model: "deepseek-chat",
    }),
  );

  const publicSettings = await savePlatformSettings({
    llm_provider: "openai",
    llm_api_key: "",
    llm_api_base: "https://api.openai.com/v1",
    llm_model: "gpt-4o-mini",
  });

  const written = JSON.parse(String(writeFileMock.mock.calls[0]?.[1]));
  expect(written.llm_api_key).toBe("");
  expect(publicSettings.llm_api_key_configured).toBe(false);
});

it("rejects invalid direct LLM settings updates before writing", async () => {
  readFileMock.mockResolvedValue(JSON.stringify({}));

  await expect(
    savePlatformSettings({ llm_provider: "deepseek" }),
  ).rejects.toMatchObject({
    code: "invalid_provider",
    field: "llm_provider",
  });
  await expect(
    savePlatformSettings({ llm_api_base: "file:///tmp/model" }),
  ).rejects.toMatchObject({
    code: "invalid_base",
    field: "llm_api_base",
  });
  await expect(
    savePlatformSettings({ llm_model: "   " }),
  ).rejects.toMatchObject({
    code: "invalid_model",
    field: "llm_model",
  });
  await expect(
    savePlatformSettings({ llm_model: "x".repeat(129) }),
  ).rejects.toMatchObject({
    code: "invalid_model",
    field: "llm_model",
  });
  await expect(
    savePlatformSettings({ llm_api_base: 123 as never }),
  ).rejects.toMatchObject({
    code: "invalid_base",
    field: "llm_api_base",
  });
  await expect(
    savePlatformSettings({ llm_api_key: { secret: true } as never }),
  ).rejects.toMatchObject({
    code: "invalid_key",
    field: "llm_api_key",
  });
  expect(writeFileMock).not.toHaveBeenCalled();
});
