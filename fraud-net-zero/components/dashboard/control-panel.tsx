"use client"

import { Zap, Scissors, FileText, Pause, Play, Gauge, Loader2 } from "lucide-react"
import { motion } from "framer-motion"

type Props = {
  paused: boolean
  onTogglePause: () => void
  speed: number
  onSpeedChange: (v: number) => void
  onTriggerAttack: () => void
  onExecuteIsolation: () => void
  onGenerateSar: () => void
  isolating: boolean
  flaggedCount: number
}

export function ControlPanel({
  paused,
  onTogglePause,
  speed,
  onSpeedChange,
  onTriggerAttack,
  onExecuteIsolation,
  onGenerateSar,
  isolating,
  flaggedCount,
}: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="glass-panel pointer-events-auto flex flex-col gap-3 rounded-xl p-3 md:flex-row md:items-center"
    >
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={onTriggerAttack}
          className="flex items-center gap-2 rounded-lg border border-border bg-muted px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
        >
          <Zap className="h-4 w-4" style={{ color: "var(--color-warning)" }} />
          Trigger Synthetic Attack
        </button>

        <button
          type="button"
          onClick={onExecuteIsolation}
          disabled={isolating || flaggedCount === 0}
          className="flex items-center gap-2 rounded-lg bg-destructive px-3 py-2 text-sm font-semibold text-destructive-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
          style={{ boxShadow: "0 0 20px -6px var(--color-destructive)" }}
        >
          {isolating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Scissors className="h-4 w-4" />}
          Execute Precision Isolation
          {flaggedCount > 0 && (
            <span className="rounded-full bg-destructive-foreground/20 px-1.5 py-0.5 font-mono text-[10px]">
              {flaggedCount}
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={onGenerateSar}
          className="flex items-center gap-2 rounded-lg border border-border bg-muted px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
        >
          <FileText className="h-4 w-4" style={{ color: "var(--color-agent-compliance)" }} />
          Generate SAR Narrative
        </button>
      </div>

      <div className="flex items-center gap-3 md:ml-auto">
        <button
          type="button"
          onClick={onTogglePause}
          aria-label={paused ? "Resume stream" : "Pause stream"}
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-muted text-foreground transition-colors hover:bg-accent"
        >
          {paused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
        </button>

        <div className="flex items-center gap-2 rounded-lg border border-border bg-muted px-3 py-1.5">
          <Gauge className="h-4 w-4 text-muted-foreground" />
          <input
            type="range"
            min={0.5}
            max={3}
            step={0.5}
            value={speed}
            onChange={(e) => onSpeedChange(Number(e.target.value))}
            className="h-1 w-24 cursor-pointer accent-[var(--color-primary)]"
            aria-label="Ingestion speed"
          />
          <span className="w-8 font-mono text-xs text-muted-foreground">{speed.toFixed(1)}x</span>
        </div>
      </div>
    </motion.div>
  )
}
