"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { RotateCcw } from "lucide-react"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"

type TaskRunRetryButtonProps = {
  taskRunId: string
}

export function TaskRunRetryButton({ taskRunId }: TaskRunRetryButtonProps) {
  const [isPending, startTransition] = React.useTransition()
  const [message, setMessage] = React.useState<string | null>(null)
  const router = useRouter()
  const t = useTranslations("TaskRuns")

  function handleRetry() {
    startTransition(async () => {
      setMessage(null)
      const response = await fetch(`/api/task-runs/${taskRunId}/retry`, {
        method: "POST",
      })

      if (!response.ok) {
        setMessage(t("retryFailed"))
        return
      }

      setMessage(t("retryStarted"))
      router.refresh()
    })
  }

  return (
    <div className="inline-flex flex-col items-end gap-1">
      <Button size="sm" variant="outline" onClick={handleRetry} disabled={isPending}>
        <RotateCcw className={isPending ? "mr-2 h-4 w-4 animate-spin" : "mr-2 h-4 w-4"} />
        {isPending ? t("retrying") : t("retry")}
      </Button>
      {message ? <span className="text-xs text-muted-foreground">{message}</span> : null}
    </div>
  )
}
