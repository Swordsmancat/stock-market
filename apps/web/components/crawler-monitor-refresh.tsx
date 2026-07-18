"use client";

import { useEffect, useTransition } from "react";
import { RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function CrawlerMonitorRefresh({ label }: { label: string }) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const refresh = () => startTransition(() => router.refresh());

  useEffect(() => {
    const interval = window.setInterval(
      () => startTransition(() => router.refresh()),
      30_000,
    );
    return () => window.clearInterval(interval);
  }, [router]);

  return (
    <Button
      type="button"
      size="icon"
      variant="outline"
      aria-label={label}
      title={label}
      onClick={refresh}
      disabled={isPending}
    >
      <RefreshCw aria-hidden="true" className={cn("h-4 w-4", isPending && "animate-spin")} />
    </Button>
  );
}
