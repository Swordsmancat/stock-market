"use client";

import * as React from "react";
import { CheckCircle2, Loader2, PlugZap } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { LlmApiPresetId, LlmConfigErrorCode } from "@/lib/llm-api-presets";

type LlmConnectionResult = {
  status: "ok";
  provider: string;
  model: string;
  latencyMs: number;
};

type LlmConnectionState =
  | { status: "idle" }
  | { status: "pending" }
  | LlmConnectionResult
  | { status: "error"; code: string };

type LlmSettingsControlLabels = {
  preset: string;
  presetHint: string;
  presetOptions: Record<LlmApiPresetId, string>;
  apiKey: string;
  apiKeyPlaceholder: string;
  apiKeyHelp: string;
  apiBase: string;
  apiBaseHint: string;
  apiBasePlaceholder: string;
  model: string;
  modelHint: string;
  modelPlaceholder: string;
  testConnection: string;
  testing: string;
  testHint: string;
  testConnected: string;
  testProvider: string;
  testModel: string;
  testLatency: string;
  testErrors: Record<string, string>;
};

type LlmSettingsControlProps = {
  initialPreset: LlmApiPresetId;
  initialApiBase: string;
  initialModel: string;
  initialErrorCode?: LlmConfigErrorCode | null;
  initialErrorMessage?: string | null;
  labels: LlmSettingsControlLabels;
};

export function LlmSettingsControl({
  initialPreset,
  initialApiBase,
  initialModel,
  initialErrorCode = null,
  initialErrorMessage = null,
  labels,
}: LlmSettingsControlProps) {
  const [preset, setPreset] = React.useState<LlmApiPresetId>(initialPreset);
  const [connection, setConnection] = React.useState<LlmConnectionState>({ status: "idle" });

  async function testConnection() {
    setConnection({ status: "pending" });
    try {
      const response = await fetch("/api/settings/llm/test", {
        method: "POST",
        cache: "no-store",
      });
      const payload = (await response.json().catch(() => null)) as Record<string, unknown> | null;
      if (
        response.ok &&
        payload?.status === "ok" &&
        payload.code === "connected" &&
        typeof payload.provider === "string" &&
        typeof payload.model === "string" &&
        typeof payload.latency_ms === "number"
      ) {
        setConnection({
          status: "ok",
          provider: payload.provider,
          model: payload.model,
          latencyMs: Math.max(0, Math.round(payload.latency_ms)),
        });
        return;
      }
      setConnection({
        status: "error",
        code: typeof payload?.code === "string" ? payload.code : "request_failed",
      });
    } catch {
      setConnection({ status: "error", code: "request_failed" });
    }
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor="llm_api_preset">
            {labels.preset}
          </label>
          <select
            id="llm_api_preset"
            name="llm_api_preset"
            value={preset}
            onChange={(event) => {
              setPreset(event.target.value as LlmApiPresetId);
              setConnection({ status: "idle" });
            }}
            aria-describedby="llm_api_preset_help"
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            {Object.entries(labels.presetOptions).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <p id="llm_api_preset_help" className="text-xs text-muted-foreground">
            {labels.presetHint}
          </p>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor="llm_api_key">
            {labels.apiKey}
          </label>
          <Input
            id="llm_api_key"
            name="llm_api_key"
            type="password"
            autoComplete="off"
            autoCapitalize="none"
            spellCheck={false}
            aria-describedby={
              initialErrorCode === "missing_key"
                ? "llm_api_key_help llm_api_key_error"
                : "llm_api_key_help"
            }
            aria-invalid={initialErrorCode === "missing_key" ? true : undefined}
            autoFocus={initialErrorCode === "missing_key"}
            placeholder={labels.apiKeyPlaceholder}
          />
          <p id="llm_api_key_help" className="text-xs text-muted-foreground">
            {labels.apiKeyHelp}
          </p>
          {initialErrorCode === "missing_key" && initialErrorMessage ? (
            <p id="llm_api_key_error" role="alert" className="text-xs text-destructive">
              {initialErrorMessage}
            </p>
          ) : null}
        </div>
      </div>

      {preset === "custom" ? (
        <div className="grid gap-4 rounded-md border border-dashed border-border/80 bg-background/50 p-3 lg:grid-cols-2">
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="llm_api_base">
              {labels.apiBase}
            </label>
            <Input
              id="llm_api_base"
              name="llm_api_base"
              type="text"
              inputMode="url"
              defaultValue={initialApiBase}
              aria-describedby={
                initialErrorCode === "invalid_base"
                  ? "llm_api_base_help llm_api_base_error"
                  : "llm_api_base_help"
              }
              aria-invalid={initialErrorCode === "invalid_base" ? true : undefined}
              autoFocus={initialErrorCode === "invalid_base"}
              placeholder={labels.apiBasePlaceholder}
            />
            <p id="llm_api_base_help" className="text-xs text-muted-foreground">
              {labels.apiBaseHint}
            </p>
            {initialErrorCode === "invalid_base" && initialErrorMessage ? (
              <p id="llm_api_base_error" role="alert" className="text-xs text-destructive">
                {initialErrorMessage}
              </p>
            ) : null}
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="llm_model">
              {labels.model}
            </label>
            <Input
              id="llm_model"
              name="llm_model"
              defaultValue={initialModel}
              maxLength={128}
              autoComplete="off"
              spellCheck={false}
              aria-describedby={
                initialErrorCode === "missing_model"
                  ? "llm_model_help llm_model_error"
                  : "llm_model_help"
              }
              aria-invalid={initialErrorCode === "missing_model" ? true : undefined}
              autoFocus={initialErrorCode === "missing_model"}
              placeholder={labels.modelPlaceholder}
            />
            <p id="llm_model_help" className="text-xs text-muted-foreground">
              {labels.modelHint}
            </p>
            {initialErrorCode === "missing_model" && initialErrorMessage ? (
              <p id="llm_model_error" role="alert" className="text-xs text-destructive">
                {initialErrorMessage}
              </p>
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="flex flex-col gap-3 border-t border-border/70 pt-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs text-muted-foreground">{labels.testHint}</p>
        <Button
          type="button"
          variant="outline"
          onClick={testConnection}
          disabled={connection.status === "pending"}
        >
          {connection.status === "pending" ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <PlugZap className="h-4 w-4" aria-hidden="true" />
          )}
          {connection.status === "pending" ? labels.testing : labels.testConnection}
        </Button>
      </div>

      {connection.status === "ok" ? (
        <div role="status" className="flex flex-wrap items-center gap-2 border border-emerald-500/40 bg-emerald-500/10 p-3 text-sm text-emerald-700 dark:text-emerald-300">
          <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
          <span className="font-medium">{labels.testConnected}</span>
          <Badge variant="outline">{labels.testProvider}: {connection.provider}</Badge>
          <Badge variant="outline">{labels.testModel}: {connection.model}</Badge>
          <Badge variant="outline">{labels.testLatency}: {connection.latencyMs} ms</Badge>
        </div>
      ) : null}

      {connection.status === "error" ? (
        <p role="alert" className="border border-destructive/35 bg-destructive/10 p-3 text-sm text-destructive">
          {labels.testErrors[connection.code] ?? labels.testErrors.request_failed}
        </p>
      ) : null}
    </div>
  );
}
