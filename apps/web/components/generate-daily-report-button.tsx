"use client";

import { useState } from "react";
import { FilePlus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";

type GenerateDailyReportButtonProps = {
  symbol: string;
  start: string;
  end: string;
  variant?: "default" | "outline" | "secondary" | "ghost";
  size?: "default" | "sm" | "lg" | "icon";
};

export function GenerateDailyReportButton({
  symbol,
  start,
  end,
  variant = "outline",
  size = "sm",
}: GenerateDailyReportButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const router = useRouter();
  const t = useTranslations("ReportsCenter");

  async function handleClick() {
    setIsLoading(true);
    setMessage(null);

    try {
      const params = new URLSearchParams({ start, end });
      const response = await fetch(
        `/api/reports/${encodeURIComponent(symbol)}/daily/generate?${params.toString()}`,
        { method: "POST" },
      );
      if (!response.ok) {
        throw new Error("Generate failed");
      }
      setMessage(t("generateSuccess"));
      router.refresh();
    } catch {
      setMessage(t("generateFailed"));
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
      {message ? <span className="text-xs text-muted-foreground">{message}</span> : null}
    </div>
  );
}
