"use client"

import * as React from "react"
import { useRouter } from "@/src/i18n/routing"
import { Search } from "lucide-react"
import { useTranslations } from "next-intl"

import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import { Button } from "@/components/ui/button"

type Instrument = {
  symbol: string;
  name: string;
  market: string;
};

export function GlobalSearch() {
  const [open, setOpen] = React.useState(false)
  const [instruments, setInstruments] = React.useState<Instrument[]>([])
  const router = useRouter()
  const t = useTranslations("TopNav")

  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setOpen((open) => !open)
      }
    }

    document.addEventListener("keydown", down)
    return () => document.removeEventListener("keydown", down)
  }, [])

  React.useEffect(() => {
    if (open && instruments.length === 0) {
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
      fetch(`${apiBaseUrl}/instruments`)
        .then((res) => res.json())
        .then((data) => {
          if (data && data.items) {
            setInstruments(data.items)
          }
        })
        .catch(console.error)
    }
  }, [open, instruments.length])

  const runCommand = React.useCallback((command: () => unknown) => {
    setOpen(false)
    command()
  }, [])

  return (
    <>
      <Button
        variant="outline"
        className="relative h-9 w-full justify-start rounded-[0.5rem] bg-background text-sm font-normal text-muted-foreground shadow-none sm:pr-12 md:w-40 lg:w-64"
        onClick={() => setOpen(true)}
      >
        <span className="hidden lg:inline-flex">{t("searchPlaceholder")}</span>
        <span className="inline-flex lg:hidden">Search...</span>
        <kbd className="pointer-events-none absolute right-[0.3rem] top-[0.3rem] hidden h-6 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex">
          <span className="text-xs">⌘</span>K
        </kbd>
      </Button>
      <CommandDialog open={open} onOpenChange={setOpen}>
        <CommandInput placeholder={t("searchPlaceholder")} />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>
          <CommandGroup heading="Instruments">
            {instruments.map((instrument) => (
              <CommandItem
                key={instrument.symbol}
                value={`${instrument.symbol} ${instrument.name}`}
                onSelect={() => {
                  runCommand(() => router.push(`/instruments/${instrument.symbol}` as any))
                }}
              >
                <Search className="mr-2 h-4 w-4" />
                <span>{instrument.symbol}</span>
                <span className="ml-2 text-muted-foreground">{instrument.name}</span>
                <span className="ml-auto text-xs text-muted-foreground">{instrument.market}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </>
  )
}
