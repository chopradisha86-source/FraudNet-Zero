"use client"

import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import { Radio, Database, Server, Wifi, RefreshCw, Moon, Sun, SlidersHorizontal, CheckCircle2, AlertTriangle } from "lucide-react"
import { NavBar } from "@/components/nav-bar"
import { useTheme } from "@/components/theme-provider"
import { checkHealth, type HealthState } from "@/lib/api"

const SERVICES: { key: keyof HealthState; label: string; icon: typeof Radio }[] = [
  { key: "kafka", label: "Kafka Broker", icon: Radio },
  { key: "memgraph", label: "Memgraph Engine", icon: Database },
  { key: "fastapi", label: "FastAPI Gateway", icon: Server },
  { key: "websockets", label: "WebSocket Stream", icon: Wifi },
]

export default function SettingsPage() {
  const { theme, setTheme } = useTheme()
  const [health, setHealth] = useState<HealthState | null>(null)
  const [checking, setChecking] = useState(false)

  const [riskThreshold, setRiskThreshold] = useState(70)
  const [cycleDepth, setCycleDepth] = useState(4)
  const [autoContain, setAutoContain] = useState(85)

  const runCheck = async () => {
    setChecking(true)
    const res = await checkHealth()
    setHealth(res)
    setChecking(false)
  }

  useEffect(() => {
    runCheck()
  }, [])

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <NavBar />
      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-8 md:px-6">
        <div className="flex items-center gap-2 text-primary">
          <SlidersHorizontal className="h-4 w-4" />
          <span className="font-mono text-xs uppercase tracking-widest">Configuration</span>
        </div>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-foreground">System Settings</h1>

        {/* Health checks */}
        <section className="glass-panel mt-6 rounded-xl p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-foreground">Pipeline Health</h2>
            <button
              type="button"
              onClick={runCheck}
              className="flex items-center gap-1.5 rounded-md border border-border bg-muted px-2.5 py-1.5 text-xs font-medium text-foreground hover:bg-accent"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${checking ? "animate-spin" : ""}`} />
              Re-check
            </button>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            {SERVICES.map((s) => {
              const ok = health?.[s.key]
              return (
                <div key={s.key} className="flex items-center gap-3 rounded-lg border border-border bg-muted/40 p-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                    <s.icon className="h-4 w-4" />
                  </span>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-foreground">{s.label}</p>
                    <p className="font-mono text-xs text-muted-foreground">
                      {health ? (ok ? "operational" : "degraded / fallback") : "checking…"}
                    </p>
                  </div>
                  {health &&
                    (ok ? (
                      <CheckCircle2 className="h-5 w-5" style={{ color: "var(--color-success)" }} />
                    ) : (
                      <AlertTriangle className="h-5 w-5" style={{ color: "var(--color-warning)" }} />
                    ))}
                </div>
              )
            })}
          </div>
        </section>

        {/* Threshold sliders */}
        <section className="glass-panel mt-4 rounded-xl p-6">
          <h2 className="text-sm font-semibold text-foreground">Detection Thresholds</h2>
          <div className="mt-4 space-y-6">
            <Slider
              label="Risk Flag Threshold"
              hint="Minimum anomaly score to flag an account as a mule."
              value={riskThreshold}
              min={0}
              max={100}
              suffix="/100"
              onChange={setRiskThreshold}
            />
            <Slider
              label="Cycle Detection Depth"
              hint="Maximum loop length the Topology Agent scans for micro-layering."
              value={cycleDepth}
              min={2}
              max={12}
              suffix=" hops"
              onChange={setCycleDepth}
            />
            <Slider
              label="Auto-Containment Trigger"
              hint="Risk score above which the Containment Agent acts autonomously."
              value={autoContain}
              min={0}
              max={100}
              suffix="/100"
              onChange={setAutoContain}
            />
          </div>
        </section>

        {/* Theme preferences */}
        <section className="glass-panel mt-4 rounded-xl p-6">
          <h2 className="text-sm font-semibold text-foreground">Theme Preferences</h2>
          <div className="mt-4 grid grid-cols-2 gap-3">
            {(
              [
                { key: "dark", label: "Command Center", icon: Moon, desc: "Deep obsidian · cyan glow" },
                { key: "light", label: "Clean Enterprise", icon: Sun, desc: "Porcelain · crisp borders" },
              ] as const
            ).map((opt) => (
              <button
                key={opt.key}
                type="button"
                onClick={() => setTheme(opt.key)}
                className={`flex flex-col gap-2 rounded-xl border p-4 text-left transition-all ${
                  theme === opt.key ? "border-primary ring-1 ring-primary" : "border-border hover:border-muted-foreground/40"
                }`}
              >
                <opt.icon className="h-5 w-5 text-primary" />
                <span className="text-sm font-semibold text-foreground">{opt.label}</span>
                <span className="text-xs text-muted-foreground">{opt.desc}</span>
              </button>
            ))}
          </div>
        </section>
      </main>
    </div>
  )
}

function Slider({
  label,
  hint,
  value,
  min,
  max,
  suffix,
  onChange,
}: {
  label: string
  hint: string
  value: number
  min: number
  max: number
  suffix: string
  onChange: (v: number) => void
}) {
  return (
    <div>
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-foreground">{label}</label>
        <span className="font-mono text-sm text-primary">
          {value}
          {suffix}
        </span>
      </div>
      <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>
      <motion.input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-2 h-1.5 w-full cursor-pointer accent-[var(--color-primary)]"
      />
    </div>
  )
}
