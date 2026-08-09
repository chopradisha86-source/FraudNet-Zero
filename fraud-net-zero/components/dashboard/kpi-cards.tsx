"use client"

import { Activity, GitBranch, ShieldCheck, Landmark } from "lucide-react"
import { motion } from "framer-motion"
import { useEffect, useState } from "react"

type Kpi = {
  label: string
  value: string
  sub: string
  icon: typeof Activity
  accent: string
}

function useThroughput() {
  const [tps, setTps] = useState(1240)
  useEffect(() => {
    const t = setInterval(() => {
      setTps((prev) => {
        const next = prev + Math.floor(Math.random() * 120 - 60)
        return Math.max(820, Math.min(1680, next))
      })
    }, 1600)
    return () => clearInterval(t)
  }, [])
  return tps
}

export function KpiCards({ nodeCount, edgeCount }: { nodeCount: number; edgeCount: number }) {
  const tps = useThroughput()

  const cards: Kpi[] = [
    {
      label: "Transaction Throughput",
      value: `${tps.toLocaleString()} tx/s`,
      sub: "Live Kafka ingestion",
      icon: Activity,
      accent: "var(--color-primary)",
    },
    {
      label: "Active Graph Nodes & Edges",
      value: `${(12450 + nodeCount).toLocaleString()} Nodes`,
      sub: `${(48210 + edgeCount).toLocaleString()} Edges tracked`,
      icon: GitBranch,
      accent: "var(--color-agent-compliance)",
    },
    {
      label: "Illicit Capital Intercepted",
      value: "$4.2M",
      sub: "+$318K in last hour",
      icon: Landmark,
      accent: "var(--color-destructive)",
    },
    {
      label: "Collateral Protection Rate",
      value: "99.8%",
      sub: "Clean user traffic preserved",
      icon: ShieldCheck,
      accent: "var(--color-success)",
    },
  ]

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((c, i) => {
        const Icon = c.icon
        return (
          <motion.div
            key={c.label}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06, duration: 0.4 }}
            className="glass-panel relative overflow-hidden rounded-xl p-4"
          >
            <div
              className="absolute inset-x-0 top-0 h-0.5"
              style={{ backgroundColor: c.accent }}
            />
            <div className="flex items-start justify-between">
              <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {c.label}
              </span>
              <span
                className="flex h-8 w-8 items-center justify-center rounded-md"
                style={{ backgroundColor: `color-mix(in srgb, ${c.accent} 16%, transparent)`, color: c.accent }}
              >
                <Icon className="h-4 w-4" />
              </span>
            </div>
            <div className="mt-3 font-mono text-2xl font-semibold tracking-tight text-foreground">
              {c.value}
            </div>
            <div className="mt-1 text-xs text-muted-foreground">{c.sub}</div>
          </motion.div>
        )
      })}
    </div>
  )
}
