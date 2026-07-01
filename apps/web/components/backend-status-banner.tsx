import { getTranslations } from "next-intl/server";
import { AlertTriangle } from "lucide-react";

import { getBackendCapabilities } from "@/lib/backend-api";

export async function BackendStatusBanner() {
  const caps = await getBackendCapabilities();
  const t = await getTranslations("System");

  if (!caps.ok) {
    return (
      <div className="mb-4 flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
        <span>{t("backendOffline")}</span>
      </div>
    );
  }

  if (caps.hasWatchlist && caps.hasPortfolios) {
    return null;
  }

  return (
    <div className="mb-4 flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-800 dark:text-amber-200">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <span>{t("backendOutdated")}</span>
    </div>
  );
}
