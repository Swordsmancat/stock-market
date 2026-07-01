"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { Plus, Trash2 } from "lucide-react"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

type WatchlistAddFormProps = {
  className?: string
}

export function WatchlistAddForm({ className }: WatchlistAddFormProps) {
  const [isPending, startTransition] = React.useTransition()
  const [message, setMessage] = React.useState<string | null>(null)
  const router = useRouter()
  const t = useTranslations("Watchlist")

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const formData = new FormData(form)
    const symbol = String(formData.get("symbol") ?? "").trim().toUpperCase()
    const market = String(formData.get("market") ?? "").trim().toUpperCase()
    const name = String(formData.get("name") ?? "").trim()

    if (!symbol || !market) {
      setMessage(t("operationFailed"))
      return
    }

    startTransition(async () => {
      setMessage(null)
      const response = await fetch("/api/watchlist/items", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ symbol, market, name: name || null }),
      })

      if (!response.ok) {
        setMessage(t("operationFailed"))
        return
      }

      form.reset()
      setMessage(t("addSuccess"))
      router.refresh()
    })
  }

  return (
    <form className={className} onSubmit={handleSubmit}>
      <div className="flex flex-col gap-2 sm:flex-row">
        <Input name="symbol" placeholder={t("symbolPlaceholder")} className="sm:w-28" />
        <Input name="market" placeholder={t("marketPlaceholder")} className="sm:w-24" />
        <Input name="name" placeholder={t("namePlaceholder")} className="sm:w-48" />
        <Button type="submit" disabled={isPending}>
          <Plus className="mr-2 h-4 w-4" />
          {isPending ? t("adding") : t("addSymbol")}
        </Button>
      </div>
      {message ? <p className="mt-2 text-sm text-muted-foreground">{message}</p> : null}
    </form>
  )
}

type WatchlistRemoveButtonProps = {
  symbol: string
  market: string
}

export function WatchlistRemoveButton({ symbol, market }: WatchlistRemoveButtonProps) {
  const [isPending, startTransition] = React.useTransition()
  const [message, setMessage] = React.useState<string | null>(null)
  const router = useRouter()
  const t = useTranslations("Watchlist")

  function handleRemove() {
    startTransition(async () => {
      setMessage(null)
      const params = new URLSearchParams({ symbol, market })
      const response = await fetch(`/api/watchlist/items?${params.toString()}`, {
        method: "DELETE",
      })

      if (!response.ok) {
        setMessage(t("operationFailed"))
        return
      }

      setMessage(t("removeSuccess"))
      router.refresh()
    })
  }

  return (
    <div className="inline-flex flex-col items-end">
      <Button
        variant="ghost"
        size="icon"
        className="text-destructive"
        title={t("remove")}
        disabled={isPending}
        onClick={handleRemove}
      >
        <Trash2 className="h-4 w-4" />
        <span className="sr-only">{isPending ? t("removing") : t("remove")}</span>
      </Button>
      {message ? <span className="sr-only">{message}</span> : null}
    </div>
  )
}
