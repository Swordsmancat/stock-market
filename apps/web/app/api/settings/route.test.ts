import { afterEach, expect, it, vi } from "vitest";

const { getPlatformSettingsMock, savePlatformSettingsMock } = vi.hoisted(() => ({
  getPlatformSettingsMock: vi.fn(),
  savePlatformSettingsMock: vi.fn(),
}));

vi.mock("@/lib/platform-settings-store", () => ({
  getPlatformSettings: getPlatformSettingsMock,
  savePlatformSettings: savePlatformSettingsMock,
}));

import { GET, PUT } from "./route";

afterEach(() => {
  getPlatformSettingsMock.mockReset();
  savePlatformSettingsMock.mockReset();
});

it("returns persisted platform settings with route source metadata", async () => {
  const storedSettings = {
    market_data_provider: "mock",
    llm_provider: "openai",
    llm_api_key: "sk-test",
    llm_api_base: "https://llm.example/v1",
    akshare_enabled: true,
    tushare_token: "tushare-token",
    llm_api_key_configured: true,
  };
  getPlatformSettingsMock.mockResolvedValue(storedSettings);

  const response = await GET();

  expect(getPlatformSettingsMock).toHaveBeenCalledOnce();
  expect(response.status).toBe(200);
  await expect(response.json()).resolves.toEqual({
    source: "platform_settings",
    ...storedSettings,
    tushare_token: "",
    tushare_token_configured: true,
  });
});

it("saves platform settings and reports whether an LLM API key is configured", async () => {
  const updatePayload = {
    market_data_provider: "tushare",
    llm_provider: "openai",
    llm_api_key: "sk-updated",
    llm_api_base: "https://api.openai.com/v1",
    akshare_enabled: false,
    tushare_token: "token-updated",
  };
  savePlatformSettingsMock.mockResolvedValue(updatePayload);

  const response = await PUT(
    new Request("http://localhost/api/settings", {
      method: "PUT",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(updatePayload),
    }),
  );

  expect(savePlatformSettingsMock).toHaveBeenCalledWith(updatePayload);
  expect(response.status).toBe(200);
  await expect(response.json()).resolves.toEqual({
    source: "platform_settings",
    ...updatePayload,
    llm_api_key_configured: true,
    tushare_token: "",
    tushare_token_configured: true,
  });
});

it("marks saved settings as not configured when the stored LLM API key is blank", async () => {
  const savedSettings = {
    market_data_provider: "mock",
    llm_provider: "mock",
    llm_api_key: "   ",
    llm_api_base: "https://api.openai.com/v1",
    akshare_enabled: false,
    tushare_token: "",
  };
  savePlatformSettingsMock.mockResolvedValue(savedSettings);

  const response = await PUT(
    new Request("http://localhost/api/settings", {
      method: "PUT",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify({ llm_api_key: "   " }),
    }),
  );

  expect(savePlatformSettingsMock).toHaveBeenCalledWith({ llm_api_key: "   " });
  expect(response.status).toBe(200);
  await expect(response.json()).resolves.toEqual({
    source: "platform_settings",
    ...savedSettings,
    llm_api_key_configured: false,
    tushare_token: "",
    tushare_token_configured: false,
  });
});
