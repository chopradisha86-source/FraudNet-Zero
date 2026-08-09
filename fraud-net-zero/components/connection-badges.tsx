"use client"

import { useEffect, useState } from "react"

type Props = {
  wsState?: "connecting" | "connected" | "fallback"
}

export function ConnectionBadges({ wsState }: Props) {
  const [pulse, setPulse] = useState(true)
  useEffect(() => {
    const t = setInterval(() => setPulse((p) => !p), 1400)
    return () => clearInterval(t)
  }, [])

  const wsConnected = wsState !== "connecting"
  const wsLabel = wsState === "connected" ? "WS: CONNECTED" : wsState === "fallback" ? "WS: FALLBACK" : "WS: LINKING"

  return (
    <div className="hidden items-center gap-2 md:flex">
      <Badge ok={wsConnected} pulse={pulse} label={wsLabel} />
      <Badge ok label="MEMGRAPH: ACTIVE" pulse={pulse} />
    </div>
  )
}

function Badge({ ok, label, pulse }: { ok: boolean; label: string; pulse: boolean }) {
  return (
    <span className="flex items-center gap-1.5 rounded-full border border-border bg-muted px-2.5 py-1 font-mono text-[10px] font-medium tracking-wide text-muted-foreground">
      <span
        className="h-1.5 w-1.5 rounded-full transition-opacity"
        style={{
          backgroundColor: ok ? "var(--color-success)" : "var(--color-warning)",
          opacity: pulse ? 1 : 0.35,
          boxShadow: `0 0 8px ${ok ? "var(--color-success)" : "var(--color-warning)"}`,
        }}
      />
      {label}
    </span>
  )
}
