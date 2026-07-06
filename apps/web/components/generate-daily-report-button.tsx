"use client";

import { useState } from "react";
import { FilePlus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { Link } from "@/src/i18n/routing";

type GeneratedReportLinks = {
  reportId: string | null;
  taskRunId: string | null;
};

type GenerateDailyReportButtonProps = {
  symbol: string;
  start: string;
  end: string;
  provider?: string | null;
  variant?: "default" | "outline" | "secondary" | "ghost";
  size?: "default" | "sm" | "lg" | "icon";
};

export function GenerateDailyReportButton({
  symbol,
  start,
  end,
  provider = null,
  variant = "outline",
  size = "sm",
}: GenerateDailyReportButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [generatedLinks, setGeneratedLinks] = useState<GeneratedReportLinks>({
    reportId: null,
    taskRunId: null,
  });
  const router = useRouter();
  const t = useTranslations("ReportsCenter");

  async function readPayload(response: Response): Promise<Record<string, unknown>> {
    try {
      return (await response.json()) as Record<string, unknown>;
    } catch {
      return {};
    }
  }

  function readString(payload: Record<string, unknown>, key: string): string | null {
    const value = payload[key];
    return typeof value === "string" && value.trim() ? value : null;
  }

  function extractErrorMessage(payload: Record<string, unknown>): string {
    const detail = payload.detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    if (detail && typeof detail === "object") {
      const detailPayload = detail as Record<string, unknown>;
      const noDataReason = readString(detailPayload, "no_data_reason");
      const message = readString(detailPayload, "message");
      return noDataReason ?? message ?? t("generateFailed");
    }
    return readString(payload, "error") ?? t("generateFailed");
  }

  async function handleClick() {
    setIsLoading(true);
    setMessage(null);
    setGeneratedLinks({ reportId: null, taskRunId: null });

    try {
      const params = new URLSearchParams({ start, end });
      if (provider) {
        params.set("provider", provider);
      }
      const response = await fetch(
        `/api/reports/${encodeURIComponent(symbol)}/daily/generate?${params.toString()}`,
        { method: "POST" },
      );
      const payload = await readPayload(response);
      if (!response.ok) {
        throw new Error(extractErrorMessage(payload));
      }
      const reportId = readString(payload, "id") ?? readString(payload, "report_id");
      const taskRunId = readString(payload, "task_run_id");
      setGeneratedLinks({ reportId, taskRunId });
      setMessage(t("generateSuccess"));
      router.refresh();
    } catch (error) {
      const reason = error instanceof Error && error.message ? error.message : t("generateFailed");
      setMessage(t("generateFailedDetail", { reason }));
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="inline-flex flex-col gap-1">
      <Button variant={variant} size={size} onClick={handleClick} disabled={isLoading}>
        <FilePlus className={`mr-2 h-4 w-4 ${isLoading ? "animate-pulse" : ""}`} />
        {isLoading ? t("generating") : t("generateReport")}
      </Button>
      {!provider ? (
        <span className="text-xs text-amber-700 dark:text-amber-300">
          未指定 provider，将使用后端默认数据源；若默认是 mock，请以报告源摘要为准。
        </span>
      ) : null}
      {message ? <span className="text-xs text-muted-foreground">{message}</span> : null}
      {generatedLinks.reportId || generatedLinks.taskRunId ? (
        <div className="flex flex-wrap gap-2 text-xs">
          {generatedLinks.reportId ? (
            <Link href={`/reports/${generatedLinks.reportId}` as any} className="text-primary hover:underline">
              {t("viewGeneratedReport")}
            </Link>
          ) : null}
          {generatedLinks.taskRunId ? (
            <Link href={`/task-runs/${generatedLinks.taskRunId}` as any} className="text-primary hover:underline">
              {t("viewTaskRun")}
            </Link>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
