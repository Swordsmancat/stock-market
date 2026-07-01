"use client"

import * as React from "react"
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts"

type Bar = {
  timestamp: string;
  close: number;
}

type PriceChartProps = {
  data: Bar[];
}

export function PriceChart({ data }: PriceChartProps) {
  const formattedData = React.useMemo(() => {
    return data.map((item, index) => {
      const maWindow = data.slice(Math.max(0, index - 2), index + 1)
      const ma3 =
        maWindow.length === 3
          ? maWindow.reduce((sum, bar) => sum + bar.close, 0) / maWindow.length
          : null
      return {
        ...item,
        ma3,
        date: new Date(item.timestamp).toLocaleDateString(),
      }
    })
  }, [data])

  if (!data || data.length === 0) {
    return (
      <div className="flex h-[300px] items-center justify-center text-sm text-muted-foreground border rounded-md">
        No price data available for chart.
      </div>
    )
  }

  const minPrice = Math.min(...data.map(d => d.close))
  const maxPrice = Math.max(...data.map(d => d.close))
  const padding = (maxPrice - minPrice) * 0.1

  return (
    <div className="h-[300px] w-full mt-4">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={formattedData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--muted-foreground))" opacity={0.2} />
          <XAxis 
            dataKey="date" 
            tickLine={false} 
            axisLine={false} 
            tickMargin={8}
            tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
            minTickGap={30}
          />
          <YAxis 
            domain={[minPrice - padding, maxPrice + padding]} 
            tickLine={false} 
            axisLine={false} 
            tickMargin={8}
            tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
            tickFormatter={(value) => `$${value.toFixed(0)}`}
            width={60}
          />
          <Tooltip 
            content={({ active, payload, label }) => {
              if (active && payload && payload.length) {
                return (
                  <div className="rounded-lg border bg-background p-2 shadow-sm">
                    <div className="grid grid-cols-2 gap-2">
                      <div className="flex flex-col">
                        <span className="text-[0.70rem] uppercase text-muted-foreground">
                          Date
                        </span>
                        <span className="font-bold text-muted-foreground">
                          {label}
                        </span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[0.70rem] uppercase text-muted-foreground">
                          Close
                        </span>
                        <span className="font-bold">
                          ${Number(payload[0].value).toFixed(2)}
                        </span>
                      </div>
                      {payload[1]?.value ? (
                        <div className="flex flex-col">
                          <span className="text-[0.70rem] uppercase text-muted-foreground">
                            MA(3)
                          </span>
                          <span className="font-bold">
                            ${Number(payload[1].value).toFixed(2)}
                          </span>
                        </div>
                      ) : null}
                    </div>
                  </div>
                )
              }
              return null
            }}
          />
          <Line
            type="monotone"
            dataKey="close"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: "hsl(var(--primary))" }}
          />
          <Line
            type="monotone"
            dataKey="ma3"
            stroke="hsl(var(--muted-foreground))"
            strokeWidth={2}
            dot={false}
            strokeDasharray="4 4"
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
