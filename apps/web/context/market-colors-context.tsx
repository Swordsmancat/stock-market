"use client";

import { createContext, useContext, type ReactNode } from "react";
import { useMarketColors, type UseMarketColorsReturn } from "@/hooks/use-market-colors";

const MarketColorsContext = createContext<UseMarketColorsReturn | null>(null);

export function MarketColorsProvider({ children }: { children: ReactNode }) {
  const marketColors = useMarketColors();

  return (
    <MarketColorsContext.Provider value={marketColors}>
      {children}
    </MarketColorsContext.Provider>
  );
}

export function useMarketColorsContext(): UseMarketColorsReturn {
  const context = useContext(MarketColorsContext);
  if (!context) {
    throw new Error("useMarketColorsContext must be used within MarketColorsProvider");
  }
  return context;
}
