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
    const priceAbove = String(formData.get("price_above") ?? "").trim()
    const rsiBelow = String(formData.get("rsi_below") ?? "").trim()

    if (!symbol || !market) {
      setMessage(t("operationFailed"))
      return
    }

    startTransition(async () => {
      setMessage(null)
      const alertRules: Record<string, number> = {}
      if (priceAbove) {
        alertRules.price_above = Number(priceAbove)
      }
      if (rsiBelow) {
        alertRules.rsi_below = Number(rsiBelow)
      }
      const response = await fetch("/api/watchlist/items", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          symbol,
          market,
          name: name || null,
          alert_rules: alertRules,
        }),
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
      <div className="grid gap-2 sm:grid-cols-[7rem_6rem_minmax(10rem,1fr)_7rem_7rem_auto]">
        <Input name="symbol" placeholder={t("symbolPlaceholder")} className="sm:w-28" />
        <Input name="market" placeholder={t("marketPlaceholder")} className="sm:w-24" />
        <Input name="name" placeholder={t("namePlaceholder")} className="sm:w-48" />
        <Input name="price_above" type="number" step="0.01" placeholder={t("priceAbovePlaceholder")} />
        <Input name="rsi_below" type="number" step="0.01" placeholder={t("rsiBelowPlaceholder")} />
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

type WatchlistEditAlertRulesFormProps = {
  symbol: string
  market: string
  name: string
  alertRules?: Record<string, number>
}

export function WatchlistEditAlertRulesForm({
  symbol,
  market,
  name,
  alertRules = {},
}: WatchlistEditAlertRulesFormProps) {
  const [isPending, startTransition] = React.useTransition()
  const [message, setMessage] = React.useState<string | null>(null)
  const router = useRouter()
  const t = useTranslations("Watchlist")

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const formData = new FormData(form)
    const priceAbove = String(formData.get("price_above") ?? "").trim()
    const rsiBelow = String(formData.get("rsi_below") ?? "").trim()
    const nextRules: Record<string, number> = {}
    if (priceAbove) {
      nextRules.price_above = Number(priceAbove)
    }
    if (rsiBelow) {
      nextRules.rsi_below = Number(rsiBelow)
    }

    startTransition(async () => {
      setMessage(null)
      const response = await fetch("/api/watchlist/items", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          symbol,
          market,
          name,
          alert_rules: nextRules,
        }),
      })
      if (!response.ok) {
        setMessage(t("operationFailed"))
        return
      }
      setMessage(t("updateAlertSuccess"))
      router.refresh()
    })
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap items-center gap-1">
      <Input
        name="price_above"
        type="number"
        step="0.01"
        defaultValue={alertRules.price_above ?? ""}
        placeholder={t("priceAbovePlaceholder")}
        className="h-8 w-24"
      />
      <Input
        name="rsi_below"
        type="number"
        step="0.01"
        defaultValue={alertRules.rsi_below ?? ""}
        placeholder={t("rsiBelowPlaceholder")}
        className="h-8 w-24"
      />
      <Button type="submit" size="sm" variant="outline" disabled={isPending}>
        {isPending ? t("savingAlerts") : t("saveAlerts")}
      </Button>
      {message ? <span className="w-full text-xs text-muted-foreground">{message}</span> : null}
    </form>
  )
}
