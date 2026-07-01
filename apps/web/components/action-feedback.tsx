"use client";

import { AlertCircle, CheckCircle2 } from "lucide-react";

import { cn } from "@/lib/utils";

type ActionFeedbackProps = {
  message: string | null;
  className?: string;
};

export function ActionFeedback({ message, className }: ActionFeedbackProps) {
  if (!message) {
    return null;
  }

  const isError = message.startsWith("❌");

  return (
    <div
      role="status"
      className={cn(
        "flex items-start gap-2 rounded-md border px-3 py-2 text-sm",
        isError
          ? "border-destructive/40 bg-destructive/10 text-destructive"
          : "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
        className,
      )}
    >
      {isError ? (
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      ) : (
        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
      )}
      <span>{message.replace(/^✅\s|^❌\s/, "")}</span>
    </div>
  );
}
