"use client";

import { LoaderCircle, Star, StarOff } from "lucide-react";
import { useRouter } from "next/navigation";
import { useId, useState } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import type { InstrumentWatchlistMembership } from "@/lib/instrument-detail";

type InstrumentWatchlistFormProps = {
  symbol: string;
  market: string;
  name?: string;
  membership: InstrumentWatchlistMembership;
};

type Feedback = {
  kind: "success" | "error";
  message: string;
};

export function InstrumentWatchlistForm({
  symbol,
  market,
  name = "",
  membership,
}: InstrumentWatchlistFormProps) {
  const router = useRouter();
  const t = useTranslations("InstrumentDetail");
  const feedbackId = useId();
  const [currentMembership, setCurrentMembership] =
    useState<InstrumentWatchlistMembership>(membership);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [pending, setPending] = useState(false);
  const unavailable = currentMembership === "unavailable";
  const watched = currentMembership === "watched";

  async function toggleWatchlist() {
    if (pending || unavailable) {
      return;
    }

    setPending(true);
    setFeedback(null);
    try {
      const response = watched
        ? await fetch(
            `/api/watchlist/items?${new URLSearchParams({ symbol, market }).toString()}`,
            { method: "DELETE" },
          )
        : await fetch("/api/watchlist/items", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({
              symbol,
              market,
              name: name || null,
            }),
          });

      if (!response.ok) {
        throw new Error("watchlist mutation failed");
      }

      const nextMembership = watched ? "not_watched" : "watched";
      setCurrentMembership(nextMembership);
      setFeedback({
        kind: "success",
        message: watched ? t("watchlistRemoved") : t("watchlistAdded"),
      });
      router.refresh();
    } catch {
      setFeedback({ kind: "error", message: t("watchlistToggleFailed") });
    } finally {
      setPending(false);
    }
  }

  const label = pending
    ? t("watchlistUpdating")
    : unavailable
      ? t("watchlistUnavailable")
      : watched
        ? t("removeFromWatchlist")
        : t("addToWatchlist");
  const Icon = pending ? LoaderCircle : watched ? StarOff : Star;

  return (
    <div className="min-w-0 sm:min-w-48">
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="min-h-11 w-full"
        disabled={pending || unavailable}
        aria-pressed={unavailable ? undefined : watched}
        aria-describedby={feedback ? feedbackId : undefined}
        onClick={toggleWatchlist}
      >
        <Icon className={pending ? "animate-spin" : undefined} />
        {label}
      </Button>
      <div className="min-h-5 pt-1 text-xs" aria-live="polite">
        {feedback ? (
          <p
            id={feedbackId}
            className={
              feedback.kind === "error"
                ? "text-destructive"
                : "text-muted-foreground"
            }
            role={feedback.kind === "error" ? "alert" : "status"}
          >
            {feedback.message}
          </p>
        ) : null}
      </div>
    </div>
  );
}
