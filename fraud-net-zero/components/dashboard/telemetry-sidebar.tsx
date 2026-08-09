"use client"

import { useEffect, useRef } from "react"
import { AnimatePresence, motion } from "framer-motion"
import { Search, Scale, Shield, FileText, Radio } from "lucide-react"
import type { AgentKind, TelemetryEvent } from "@/lib/types"

const AGENT_UI: Record<AgentKind, { label: string; token: string; icon: typeof Search }> = {
  topology: { label: "Topology", token: "var(--color-agent-topology)", icon: Search },
  risk: { label: "Risk Scoring", token: "var(--color-agent-risk)", icon: Scale },
  containment: { label: "Containment", token: "var(--color-agent-containment)", icon: Shield },
  compliance: { label: "Compliance", token: "var(--color-agent-compliance)", icon: FileText },
}

function ts(t: number) {
  const d = new Date(t)
  return d.toLocaleTimeString("en-US", { hour12: false }) + "." + String(d.getMilliseconds()).padStart(3, "0")
}

export function TelemetrySidebar({
  events,
  state,
}: {
  events: TelemetryEvent[]
  state: "connecting" | "connected" | "fallback"
}) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [events])

  return (
    <div className="glass-panel flex h-full flex-col overflow-hidden rounded-xl">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Radio className="h-4 w-4 text-primary" />
          <h2 className="text-sm font-semibold text-foreground">Multi-Agent Telemetry</h2>
        </div>
        <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
          <span
            className="h-1.5 w-1.5 animate-pulse rounded-full"
            style={{ backgroundColor: state === "connected" ? "var(--color-success)" : "var(--color-warning)" }}
          />
          {state === "connected" ? "live" : "fallback"}
        </span>
      </div>

      <div
        ref={scrollRef}
        className="no-scrollbar flex-1 space-y-1.5 overflow-y-auto bg-[var(--color-terminal)] p-3 font-mono text-xs"
      >
        <AnimatePresence initial={false}>
          {events.map((evt) => {
            const ui = AGENT_UI[evt.agent]
            const Icon = ui.icon
            return (
              <motion.div
                key={evt.id}
                initial={{ opacity: 0, x: 8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="flex gap-2 rounded-md px-1.5 py-1"
              >
                <span className="shrink-0 text-[10px] leading-5 text-muted-foreground">{ts(evt.ts)}</span>
                <span
                  className="flex h-5 shrink-0 items-center gap-1 rounded px-1.5 text-[9px] font-semibold uppercase tracking-wide"
                  style={{
                    color: ui.token,
                    backgroundColor: `color-mix(in srgb, ${ui.token} 14%, transparent)`,
                  }}
                >
                  <Icon className="h-2.5 w-2.5" />
                  {ui.label}
                </span>
                <span className="leading-5 text-[var(--color-terminal-foreground)]">
                  <span
                    className="mr-1 text-[9px] font-bold uppercase"
                    style={{ color: evt.type === "CYCLE_ALERT" || evt.type === "CONTAINMENT_EXECUTION" ? "var(--color-destructive)" : "var(--color-muted-foreground)" }}
                  >
                    [{evt.type}]
                  </span>
                  {evt.message}
                </span>
              </motion.div>
            )
          })}
        </AnimatePresence>
        {events.length === 0 && (
          <div className="py-8 text-center text-muted-foreground">Awaiting agent telemetry…</div>
        )}
      </div>
    </div>
  )
}
