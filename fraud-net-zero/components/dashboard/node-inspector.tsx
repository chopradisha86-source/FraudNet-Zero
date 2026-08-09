"use client"

import { AnimatePresence, motion } from "framer-motion"
import { X, Snowflake, FileText, Users, Hexagon } from "lucide-react"
import type { GraphNode } from "@/lib/types"

type Props = {
  node: GraphNode | null
  neighborCount: number
  onClose: () => void
  onFreeze: (node: GraphNode) => void
  onGenerateSar: (node: GraphNode) => void
}

const STATUS_COLOR: Record<string, string> = {
  ACTIVE: "var(--color-success)",
  "UNDER MONITORING": "var(--color-warning)",
  CONTAINED: "var(--color-node-frozen)",
}

function RiskGauge({ score }: { score: number }) {
  const color = score >= 70 ? "var(--color-destructive)" : score >= 40 ? "var(--color-warning)" : "var(--color-success)"
  const r = 46
  const circ = 2 * Math.PI * r
  const offset = circ - (score / 100) * circ
  return (
    <div className="relative flex h-32 w-32 items-center justify-center">
      <svg className="h-32 w-32 -rotate-90" viewBox="0 0 110 110">
        <circle cx="55" cy="55" r={r} fill="none" stroke="var(--color-muted)" strokeWidth="8" />
        <motion.circle
          cx="55"
          cy="55"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circ}
          initial={{ strokeDashoffset: circ }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          style={{ filter: `drop-shadow(0 0 6px ${color})` }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="font-mono text-3xl font-bold" style={{ color }}>
          {score}
        </span>
        <span className="text-[10px] uppercase tracking-wide text-muted-foreground">risk score</span>
      </div>
    </div>
  )
}

export function NodeInspector({ node, neighborCount, onClose, onFreeze, onGenerateSar }: Props) {
  return (
    <AnimatePresence>
      {node && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-background/60 backdrop-blur-sm"
          />
          <motion.aside
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 320, damping: 34 }}
            className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-border bg-popover text-popover-foreground shadow-2xl"
          >
            <div className="flex items-center justify-between border-b border-border px-5 py-4">
              <div className="flex items-center gap-2">
                <Hexagon className="h-4 w-4 text-primary" />
                <h2 className="text-sm font-semibold">Node Inspector</h2>
              </div>
              <button
                type="button"
                onClick={onClose}
                aria-label="Close inspector"
                className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="no-scrollbar flex-1 space-y-6 overflow-y-auto px-5 py-5">
              <div>
                <span className="text-[10px] uppercase tracking-wide text-muted-foreground">SHA-256 Account ID</span>
                <p className="mt-1 break-all font-mono text-xs text-foreground">{node.id}</p>
                <div className="mt-3 flex items-center gap-2">
                  <span
                    className="rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide"
                    style={{
                      color: STATUS_COLOR[node.status],
                      backgroundColor: `color-mix(in srgb, ${STATUS_COLOR[node.status]} 15%, transparent)`,
                    }}
                  >
                    {node.status}
                  </span>
                  <span className="font-mono text-xs text-muted-foreground">
                    Balance ${node.balance.toLocaleString()}
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-center rounded-xl border border-border bg-muted/40 py-4">
                <RiskGauge score={node.riskScore} />
              </div>

              <div>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Top 5 SHAP Feature Attributions
                </h3>
                <div className="space-y-2">
                  {node.shap.map((s) => {
                    const positive = s.value >= 0
                    const width = Math.min(100, Math.abs(s.value) * 1.6)
                    return (
                      <div key={s.feature} className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-foreground">{s.feature}</span>
                          <span
                            className="font-mono font-medium"
                            style={{ color: positive ? "var(--color-destructive)" : "var(--color-success)" }}
                          >
                            {positive ? "+" : ""}
                            {s.value}%
                          </span>
                        </div>
                        <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${width}%` }}
                            transition={{ duration: 0.5 }}
                            className="h-full rounded-full"
                            style={{ backgroundColor: positive ? "var(--color-destructive)" : "var(--color-success)" }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border border-border bg-muted/40 p-3">
                  <div className="flex items-center gap-1.5 text-muted-foreground">
                    <Users className="h-3.5 w-3.5" />
                    <span className="text-[10px] uppercase tracking-wide">Graph Neighbors</span>
                  </div>
                  <p className="mt-1 font-mono text-lg font-semibold text-foreground">{neighborCount}</p>
                </div>
                <div className="rounded-lg border border-border bg-muted/40 p-3">
                  <div className="flex items-center gap-1.5 text-muted-foreground">
                    <Hexagon className="h-3.5 w-3.5" />
                    <span className="text-[10px] uppercase tracking-wide">Louvain Cluster</span>
                  </div>
                  <p className="mt-1 font-mono text-lg font-semibold text-foreground">#{node.cluster}</p>
                </div>
              </div>
            </div>

            <div className="flex gap-2 border-t border-border px-5 py-4">
              <button
                type="button"
                onClick={() => onFreeze(node)}
                disabled={node.kind === "frozen"}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg border border-border bg-muted px-3 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-40"
              >
                <Snowflake className="h-4 w-4" />
                {node.kind === "frozen" ? "Frozen" : "Freeze Account"}
              </button>
              <button
                type="button"
                onClick={() => onGenerateSar(node)}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-primary px-3 py-2.5 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90"
              >
                <FileText className="h-4 w-4" />
                Generate SAR
              </button>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
