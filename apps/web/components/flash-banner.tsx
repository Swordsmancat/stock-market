import { AlertCircle, CheckCircle2 } from "lucide-react";

type FlashBannerProps = {
  variant: "success" | "error";
  message: string;
};

export function FlashBanner({ variant, message }: FlashBannerProps) {
  const isError = variant === "error";

  return (
    <div
      role="status"
      className={
        isError
          ? "flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive"
          : "flex items-start gap-2 rounded-md border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-700 dark:text-emerald-300"
      }
    >
      {isError ? (
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      ) : (
        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
      )}
      <span>{message}</span>
    </div>
  );
}
