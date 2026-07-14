"use client";

import * as React from "react";
import { AlertTriangle, Database, RefreshCw, Search, ShieldCheck, Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";

import {
  FinancialTerminalCard,
  FinancialTerminalCardContent,
  FinancialTerminalCardHeader,
  FinancialTerminalSurface,
} from "@/components/financial-terminal-section";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Link } from "@/src/i18n/routing";

export type StockSelectionProfile = {
  id: string;
  label: string;
  description: string;
  criteria: Record<string, unknown>;
  supported_overrides?: string[];
};

export type StockSelectionProfilesPayload = {
  status?: string;
  items?: StockSelectionProfile[];
};

export type StockUniverseStatusPayload = {
  status?: string;
  active_instrument_count?: number;
  managed_instrument_count?: number;
  latest_sync?: {
    created_at?: string | null;
    as_of?: string | null;
    total_count?: number;
    status?: string;
  } | null;
};

type DiscoveryItem = {
  symbol: string;
  name?: string | null;
  market?: string | null;
  score?: number | null;
  matched_rules?: Array<{ code?: string; status?: string }>;
};

type StockDiscoveryPayload = {
  status?: string;
  shortlist?: DiscoveryItem[];
  shortlist_count?: number;
  explanation_markdown?: string;
  citations?: Array<{ id: string; symbol?: string; source_type?: string }>;
  diagnostics?: Array<{ code?: string; message?: string; dimension?: string; count?: number }>;
  coverage?: {
    candidate_count?: number;
    evaluated_count?: number;
    matched_count?: number;
    evidence?: Record<string, { coverage_ratio?: number; missing_count?: number }>;
  } | null;
  model?: { used_llm?: boolean; name?: string; fallback_reason?: string | null };
};

type TaskDispatchPayload = {
  task_run?: {
    id?: string;
    status?: string;
  };
};

type StockDiscoveryPanelProps = {
  initialProfiles: StockSelectionProfilesPayload | null;
  initialUniverseStatus: StockUniverseStatusPayload | null;
};

export function StockDiscoveryPanel({
  initialProfiles,
  initialUniverseStatus,
}: StockDiscoveryPanelProps) {
  const t = useTranslations("StockDiscovery");
  const router = useRouter();
  const profiles = initialProfiles?.items ?? [];
  const [profileId, setProfileId] = React.useState(profiles[0]?.id ?? "balanced_research");
  const selectedProfile = profiles.find((profile) => profile.id === profileId) ?? profiles[0];
  const [criteriaDraft, setCriteriaDraft] = React.useState<Record<string, string | boolean>>(
    () => criteriaToDraft(selectedProfile?.criteria ?? {}),
  );
  const [universeStatus, setUniverseStatus] = React.useState(initialUniverseStatus);
  const [universePending, setUniversePending] = React.useState(false);
  const [discoveryPending, setDiscoveryPending] = React.useState(false);
  const [taskRunId, setTaskRunId] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<StockDiscoveryPayload | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setCriteriaDraft(criteriaToDraft(selectedProfile?.criteria ?? {}));
  }, [selectedProfile]);

  async function refreshUniverse() {
    setUniversePending(true);
    setError(null);
    try {
      const response = await fetch("/api/ingestion/instrument-universe", { method: "POST" });
      const payload = (await response.json()) as TaskDispatchPayload & { detail?: string };
      if (!response.ok) {
        throw new Error(payload.detail ?? t("refreshFailed"));
      }
      setTaskRunId(payload.task_run?.id ?? null);
      const statusResponse = await fetch("/api/stock-selection/universe-status", {
        cache: "no-store",
      });
      if (statusResponse.ok) {
        setUniverseStatus((await statusResponse.json()) as StockUniverseStatusPayload);
      }
      router.refresh();
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : t("refreshFailed"));
    } finally {
      setUniversePending(false);
    }
  }

  async function runDiscovery() {
    setDiscoveryPending(true);
    setError(null);
    try {
      const response = await fetch("/api/stock-selection/discover", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          profile_id: profileId,
          market: "CN",
          asset_type: "stock",
          shortlist_limit: 10,
          locale: document.documentElement.lang === "en" ? "en" : "zh",
          overrides: draftToOverrides(criteriaDraft, selectedProfile?.criteria ?? {}),
        }),
      });
      const payload = (await response.json()) as StockDiscoveryPayload & { detail?: string };
      if (!response.ok) {
        throw new Error(payload.detail ?? t("discoverFailed"));
      }
      setResult(payload);
    } catch (discoveryError) {
      setError(discoveryError instanceof Error ? discoveryError.message : t("discoverFailed"));
    } finally {
      setDiscoveryPending(false);
    }
  }

  function handoffSymbol(symbol: string) {
    window.dispatchEvent(
      new CustomEvent("stock-discovery:select-symbol", { detail: { symbol } }),
    );
    document.getElementById("ai-research-desk")?.scrollIntoView({ behavior: "smooth" });
  }

  const evidenceCoverage = Object.entries(result?.coverage?.evidence ?? {});

  return (
    <FinancialTerminalCard>
      <FinancialTerminalCardHeader>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-xl">
              <Sparkles className="h-5 w-5" />
              {t("title")}
            </CardTitle>
            <CardDescription className="mt-1">{t("description")}</CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={() => void runDiscovery()} disabled={discoveryPending || !selectedProfile}>
              <Search className={discoveryPending ? "h-4 w-4 animate-pulse" : "h-4 w-4"} />
              {discoveryPending ? t("discovering") : t("discover")}
            </Button>
          </div>
        </div>
      </FinancialTerminalCardHeader>
      <FinancialTerminalCardContent className="space-y-5">
        <div className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
          <div className="space-y-2">
            <label className="text-sm font-semibold" htmlFor="stock-discovery-profile">
              {t("profile")}
            </label>
            <Select value={profileId} onValueChange={setProfileId}>
              <SelectTrigger id="stock-discovery-profile" aria-label={t("profile")}>
                <SelectValue placeholder={t("profilePlaceholder")} />
              </SelectTrigger>
              <SelectContent>
                {profiles.map((profile) => (
                  <SelectItem key={profile.id} value={profile.id}>{profile.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs leading-5 text-muted-foreground">
              {selectedProfile?.description ?? t("profilesUnavailable")}
            </p>
          </div>

          <div className="space-y-2">
            <div className="text-sm font-semibold">{t("criteria")}</div>
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
              {Object.entries(selectedProfile?.criteria ?? {}).map(([key, value]) => (
                <label key={key} className="space-y-1 text-xs text-muted-foreground">
                  <span>{humanize(key)}</span>
                  {typeof value === "boolean" ? (
                    <span className="flex h-10 items-center gap-2 rounded-md border border-input bg-background px-3">
                      <input
                        type="checkbox"
                        checked={Boolean(criteriaDraft[key])}
                        onChange={(event) => setCriteriaDraft((current) => ({ ...current, [key]: event.target.checked }))}
                      />
                      {criteriaDraft[key] ? t("enabled") : t("disabled")}
                    </span>
                  ) : (
                    <Input
                      type="number"
                      step="any"
                      value={String(criteriaDraft[key] ?? "")}
                      onChange={(event) => setCriteriaDraft((current) => ({ ...current, [key]: event.target.value }))}
                    />
                  )}
                </label>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">{t("criteriaBoundary")}</p>
          </div>
        </div>

        {error ? (
          <div role="alert" className="flex items-start gap-2 border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            {error}
          </div>
        ) : null}

        {result ? (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <Badge variant="secondary">{t("evaluated", { count: result.coverage?.evaluated_count ?? 0 })}</Badge>
              <Badge variant="secondary">{t("matched", { count: result.coverage?.matched_count ?? 0 })}</Badge>
              <Badge variant={result.model?.used_llm ? "default" : "outline"}>
                {result.model?.used_llm ? t("aiExplanation") : t("deterministicFallback")}
              </Badge>
              <Badge variant="outline"><ShieldCheck className="h-3 w-3" />{t("researchOnly")}</Badge>
            </div>

            {evidenceCoverage.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {evidenceCoverage.map(([source, coverage]) => (
                  <Badge key={source} variant="outline">
                    {humanize(source)}: {Math.round((coverage.coverage_ratio ?? 0) * 100)}%
                  </Badge>
                ))}
              </div>
            ) : null}

            {(result.shortlist ?? []).length > 0 ? (
              <FinancialTerminalSurface className="overflow-hidden p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t("rank")}</TableHead>
                      <TableHead>{t("symbol")}</TableHead>
                      <TableHead>{t("score")}</TableHead>
                      <TableHead>{t("matchedRules")}</TableHead>
                      <TableHead className="text-right">{t("handoff")}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(result.shortlist ?? []).map((item, index) => (
                      <TableRow key={item.symbol}>
                        <TableCell className="font-mono">{index + 1}</TableCell>
                        <TableCell>
                          <div className="font-mono font-semibold">{item.symbol}</div>
                          <div className="text-xs text-muted-foreground">{item.name}</div>
                        </TableCell>
                        <TableCell className="font-mono">{item.score?.toFixed(4) ?? "—"}</TableCell>
                        <TableCell>{item.matched_rules?.map((rule) => rule.code).filter(Boolean).join(", ") || "—"}</TableCell>
                        <TableCell className="text-right">
                          <Button size="sm" variant="outline" onClick={() => handoffSymbol(item.symbol)}>
                            {t("useInDesk")}
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </FinancialTerminalSurface>
            ) : (
              <FinancialTerminalSurface className="p-4 text-sm text-muted-foreground">
                {t("emptyShortlist")}
              </FinancialTerminalSurface>
            )}

            <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
              <FinancialTerminalSurface className="p-4">
                <div className="mb-2 text-sm font-semibold">{t("explanation")}</div>
                <pre className="whitespace-pre-wrap font-sans text-sm leading-6">{result.explanation_markdown}</pre>
              </FinancialTerminalSurface>
              <div className="space-y-3">
                <FinancialTerminalSurface className="p-3">
                  <div className="text-sm font-semibold">{t("citations")}</div>
                  <div className="mt-2 space-y-1">
                    {(result.citations ?? []).slice(0, 12).map((citation) => (
                      <div key={citation.id} className="break-all font-mono text-[11px] text-muted-foreground">{citation.id}</div>
                    ))}
                    {(result.citations ?? []).length === 0 ? <p className="text-xs text-muted-foreground">{t("noCitations")}</p> : null}
                  </div>
                </FinancialTerminalSurface>
                <FinancialTerminalSurface className="p-3">
                  <div className="text-sm font-semibold">{t("diagnostics")}</div>
                  <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-muted-foreground">
                    {(result.diagnostics ?? []).slice(0, 10).map((diagnostic, index) => (
                      <li key={`${diagnostic.code ?? "diagnostic"}-${index}`}>
                        {diagnostic.code ?? diagnostic.dimension}: {diagnostic.message ?? diagnostic.count ?? t("unavailable")}
                      </li>
                    ))}
                  </ul>
                </FinancialTerminalSurface>
              </div>
            </div>
          </div>
        ) : null}

        <details className="rounded-md border border-dashed border-border/80 bg-card/95 p-4">
          <summary className="cursor-pointer text-sm font-semibold text-foreground">
            <span className="inline-flex items-center gap-2">
              <Database className="h-4 w-4" aria-hidden="true" />
              {t("universeStatus")}
            </span>
          </summary>
          <div className="mt-4 space-y-4">
            <div className="flex justify-end">
              <Button
                type="button"
                variant="outline"
                onClick={() => void refreshUniverse()}
                disabled={universePending}
              >
                <RefreshCw className={universePending ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
                {universePending ? t("refreshing") : t("refreshUniverse")}
              </Button>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <Metric label={t("universeStatus")} value={universeStatus?.status ?? t("unavailable")} />
              <Metric label={t("activeInstruments")} value={formatNumber(universeStatus?.active_instrument_count)} />
              <Metric label={t("managedInstruments")} value={formatNumber(universeStatus?.managed_instrument_count)} />
              <Metric
                label={t("latestSync")}
                value={universeStatus?.latest_sync?.created_at ?? universeStatus?.latest_sync?.as_of ?? t("unavailable")}
              />
            </div>

            {taskRunId ? (
              <FinancialTerminalSurface className="flex flex-wrap items-center justify-between gap-2 border-primary/30 bg-primary/5 p-3 text-sm">
                <span>{t("refreshQueued")}</span>
                <Button size="sm" variant="outline" asChild>
                  <Link href={`/task-runs/${taskRunId}`}>{t("openTaskRun")}</Link>
                </Button>
              </FinancialTerminalSurface>
            ) : null}
          </div>
        </details>
      </FinancialTerminalCardContent>
    </FinancialTerminalCard>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <FinancialTerminalSurface className="p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 break-all font-mono text-sm font-semibold">{value}</div>
    </FinancialTerminalSurface>
  );
}

function criteriaToDraft(criteria: Record<string, unknown>): Record<string, string | boolean> {
  return Object.fromEntries(
    Object.entries(criteria).map(([key, value]) => [key, typeof value === "boolean" ? value : String(value ?? "")]),
  );
}

function draftToOverrides(
  draft: Record<string, string | boolean>,
  defaults: Record<string, unknown>,
): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(draft).map(([key, value]) => {
      if (typeof defaults[key] === "boolean") {
        return [key, Boolean(value)];
      }
      const numericValue = Number(value);
      return [key, Number.isFinite(numericValue) ? numericValue : value];
    }),
  );
}

function formatNumber(value: number | null | undefined): string {
  return typeof value === "number" ? value.toLocaleString() : "—";
}

function humanize(value: string): string {
  return value.replaceAll("_", " ");
}
