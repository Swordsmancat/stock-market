export const LLM_API_PRESET_IDS = [
  "disabled",
  "deepseek",
  "openai",
  "custom",
] as const;

export type LlmApiPresetId = (typeof LLM_API_PRESET_IDS)[number];

export const LLM_CONFIG_ERROR_CODES = [
  "invalid_base",
  "missing_model",
  "missing_key",
] as const;

export type LlmConfigErrorCode =
  (typeof LLM_CONFIG_ERROR_CODES)[number];

type ResolvedLlmApiSettings = {
  llm_provider: "mock" | "openai";
  llm_api_base: string;
  llm_model: string;
};

type LlmApiPresetResolution =
  | { ok: true; settings: ResolvedLlmApiSettings }
  | { ok: false; error: LlmConfigErrorCode };

export const OPENAI_API_BASE = "https://api.openai.com/v1";
export const OPENAI_MODEL = "gpt-4o-mini";
export const DEEPSEEK_API_BASE = "https://api.deepseek.com/v1";
export const DEEPSEEK_MODEL = "deepseek-chat";

export function normalizeLlmApiBase(value: string): string {
  return value.trim().replace(/\/+$/, "");
}

export function normalizeLlmModel(value: unknown): string {
  return String(value ?? "").trim();
}

export function isValidLlmApiBase(value: string): boolean {
  const normalized = normalizeLlmApiBase(value);
  const normalizedLower = normalized.toLowerCase();
  if (
    !normalizedLower.startsWith("http://") &&
    !normalizedLower.startsWith("https://")
  ) {
    return false;
  }
  if (/[\s\\\u0000-\u001f\u007f]/u.test(normalized)) {
    return false;
  }
  const authority = normalized.split("://", 2)[1]?.split("/", 1)[0] ?? "";
  if (!authority || authority.includes("%")) {
    return false;
  }
  try {
    const parsed = new URL(normalized);
    return (
      ["http:", "https:"].includes(parsed.protocol) &&
      Boolean(parsed.hostname) &&
      !parsed.username &&
      !parsed.password &&
      !normalized.includes("?") &&
      !normalized.includes("#")
    );
  } catch {
    return false;
  }
}

export function normalizeLlmApiPresetId(value: unknown): LlmApiPresetId {
  return LLM_API_PRESET_IDS.includes(value as LlmApiPresetId)
    ? (value as LlmApiPresetId)
    : "disabled";
}

export function inferLlmApiPreset(settings: {
  llm_provider: string;
  llm_api_base: string;
  llm_model: string;
}): LlmApiPresetId {
  if (settings.llm_provider.trim().toLowerCase() === "mock") {
    return "disabled";
  }

  const apiBase = normalizeLlmApiBase(settings.llm_api_base);
  const model = normalizeLlmModel(settings.llm_model);
  if (apiBase === DEEPSEEK_API_BASE && model === DEEPSEEK_MODEL) {
    return "deepseek";
  }
  if (apiBase === OPENAI_API_BASE && model === OPENAI_MODEL) {
    return "openai";
  }
  return "custom";
}

export function resolveLlmApiPreset(
  presetValue: unknown,
  customApiBase: unknown,
  customModel: unknown,
): LlmApiPresetResolution {
  const preset = normalizeLlmApiPresetId(presetValue);
  if (preset === "disabled") {
    return {
      ok: true,
      settings: {
        llm_provider: "mock",
        llm_api_base: OPENAI_API_BASE,
        llm_model: OPENAI_MODEL,
      },
    };
  }
  if (preset === "deepseek") {
    return {
      ok: true,
      settings: {
        llm_provider: "openai",
        llm_api_base: DEEPSEEK_API_BASE,
        llm_model: DEEPSEEK_MODEL,
      },
    };
  }
  if (preset === "openai") {
    return {
      ok: true,
      settings: {
        llm_provider: "openai",
        llm_api_base: OPENAI_API_BASE,
        llm_model: OPENAI_MODEL,
      },
    };
  }

  const llmApiBase = normalizeLlmApiBase(String(customApiBase ?? ""));
  if (!isValidLlmApiBase(llmApiBase)) {
    return { ok: false, error: "invalid_base" };
  }

  const llmModel = normalizeLlmModel(customModel);
  if (!llmModel) {
    return { ok: false, error: "missing_model" };
  }

  return {
    ok: true,
    settings: {
      llm_provider: "openai",
      llm_api_base: llmApiBase,
      llm_model: llmModel,
    },
  };
}
