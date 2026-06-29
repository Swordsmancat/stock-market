"use client";

import { useState } from "react";

type AnalysisRefreshPayload = {
  symbol: string;
  status: string;
  report: { report_type: string };
};

type AnalysisRefreshButtonProps = {
  symbol: string;
  market: string;
  start: string;
  end: string;
  maWindow: number;
};

export function AnalysisRefreshButton({
  symbol,
  market,
  start,
  end,
  maWindow,
}: AnalysisRefreshButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function handleClick() {
    setIsLoading(true);
    setMessage(null);

    try {
      const params = new URLSearchParams({
        symbol,
        market,
        start,
        end,
        ma_window: String(maWindow),
      });
      const response = await fetch(`/api/analysis/refresh?${params.toString()}`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error("Analysis refresh request failed");
      }
      const payload = (await response.json()) as AnalysisRefreshPayload;
      setMessage(`分析刷新完成：${payload.symbol}，报告已生成`);
    } catch {
      setMessage("分析刷新失败，请稍后重试");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div>
      <button type="button" onClick={handleClick} disabled={isLoading}>
        {isLoading ? "分析刷新中..." : "刷新股票分析"}
      </button>
      {message ? <p>{message}</p> : null}
    </div>
  );
}
