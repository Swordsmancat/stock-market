"use client";

import { useState } from "react";

type IngestionPayload = {
  status: string;
  market: string;
  bar_count: number;
};

type IngestionButtonProps = {
  market: string;
  start: string;
  end: string;
};

export function IngestionButton({ market, start, end }: IngestionButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function handleClick() {
    setIsLoading(true);
    setMessage(null);

    try {
      const params = new URLSearchParams({ market, start, end });
      const response = await fetch(`/api/ingestion/mock-snapshot?${params.toString()}`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error("Ingestion request failed");
      }
      const payload = (await response.json()) as IngestionPayload;
      setMessage(`采集完成：${payload.market}，${payload.bar_count} 条行情写入数据库`);
    } catch {
      setMessage("采集失败，请稍后重试");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div>
      <button type="button" onClick={handleClick} disabled={isLoading}>
        {isLoading ? "采集中..." : "触发行情采集"}
      </button>
      {message ? <p>{message}</p> : null}
    </div>
  );
}
