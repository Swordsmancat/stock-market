import { afterEach, expect, it, vi } from "vitest";

const { getPlatformSettingsMock, savePlatformSettingsMock } = vi.hoisted(() => ({
  getPlatformSettingsMock: vi.fn(),
  savePlatformSettingsMock: vi.fn(),
}));

vi.mock("@/lib/platform-settings-store", async (importOriginal) => {
  const actual = await importOriginal<
    typeof import("@/lib/platform-settings-store")
  >();
  return {
    ...actual,
    getPlatformSettings: getPlatformSettingsMock,
    savePlatformSettings: savePlatformSettingsMock,
  };
});

import { PlatformSettingsValidationError } from "@/lib/platform-settings-store";
import { GET, PUT } from "./route";

afterEach(() => {
  getPlatformSettingsMock.mockReset();
  savePlatformSettingsMock.mockReset();
});

it("redacts the LLM API key on both GET and PUT", async () => {
  const privateSettings = {
    llm_provider: "openai",
    llm_api_key: "alias-secret",
    llm_api_base: "https://api.deepseek.com/v1",
    llm_model: "deepseek-chat",
  };
  getPlatformSettingsMock.mockResolvedValue(privateSettings);
  savePlatformSettingsMock.mockResolvedValue(privateSettings);

  const getResponse = await GET();
  const putResponse = await PUT(
    new Request("http://localhost/api/platform-settings", {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ llm_api_key: "alias-secret" }),
    }),
  );

  expect(getResponse.status).toBe(200);
  expect(putResponse.status).toBe(200);
  for (const response of [getResponse, putResponse]) {
    const payload = await response.json();
    expect(payload.llm_api_key).toBe("");
    expect(payload.llm_api_key_configured).toBe(true);
    expect(JSON.stringify(payload)).not.toContain("alias-secret");
  }
});

it("uses the same field-level LLM validation response as the settings alias", async () => {
  savePlatformSettingsMock.mockRejectedValue(
    new PlatformSettingsValidationError(
      "invalid_provider",
      "llm_provider",
      "llm_provider must be 'mock' or 'openai'",
    ),
  );

  const response = await PUT(
    new Request("http://localhost/api/platform-settings", {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ llm_provider: "deepseek" }),
    }),
  );

  expect(response.status).toBe(422);
  await expect(response.json()).resolves.toEqual({
    code: "invalid_provider",
    field: "llm_provider",
    detail: "llm_provider must be 'mock' or 'openai'",
  });
});

it("rejects a non-object payload without writing settings", async () => {
  const response = await PUT(
    new Request("http://localhost/api/platform-settings", {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: "null",
    }),
  );

  expect(response.status).toBe(422);
  expect(savePlatformSettingsMock).not.toHaveBeenCalled();
});
