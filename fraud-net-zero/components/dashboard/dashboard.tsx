"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { NavBar } from "@/components/nav-bar"
import { KpiCards } from "./kpi-cards"
import { GraphCanvas } from "./graph-canvas"
import { ControlPanel } from "./control-panel"
import { TelemetrySidebar } from "./telemetry-sidebar"
import { NodeInspector } from "./node-inspector"
import { SarModal } from "./sar-modal"
import { useTelemetry } from "@/lib/use-telemetry"
import { generateInitialGraph, generateAttackRing } from "@/lib/mock-data"
import { executeContainment, generateSar } from "@/lib/api"
import type { GraphData, GraphNode, SarReport } from "@/lib/types"

export function Dashboard() {
  // Generated after mount to avoid SSR/client hydration mismatch (uses Math.random()).
  const [data, setData] = useState<GraphData>({ nodes: [], links: [] })

  useEffect(() => {
    setData(generateInitialGraph())
  }, [])

  const [selected, setSelected] = useState<GraphNode | null>(null)
  const [isolating, setIsolating] = useState(false)
  const [sarOpen, setSarOpen] = useState(false)
  const [sarLoading, setSarLoading] = useState(false)
  const [sarReport, setSarReport] = useState<SarReport | null>(null)

  const { events, state, paused, setPaused, speed, setSpeed, emit } = useTelemetry()

  const flaggedNodes = useMemo(() => data.nodes.filter((n) => n.kind === "flagged"), [data])

  const neighborCount = useCallback(
    (id: string) => {
      let count = 0
      for (const l of data.links) {
        const s = typeof l.source === "string" ? l.source : (l.source as any)?.id
        const t = typeof l.target === "string" ? l.target : (l.target as any)?.id
        if (s === id || t === id) count++
      }
      return count
    },
    [data.links],
  )

  const handleTriggerAttack = useCallback(() => {
    const ring = generateAttackRing(48)
    setData((prev) => ({
      nodes: [...prev.nodes, ...ring.nodes],
      links: [...prev.links, ...ring.links],
    }))
    emit("topology", "CYCLE_ALERT", `Synthetic micro-layering ring injected · ${ring.nodes.length} mule nodes · cyclic depth confirmed`)
    setTimeout(
      () => emit("risk", "RISK_SCORES", `Batch anomaly scoring on ${ring.nodes.length} new nodes · mean risk ${Math.round(75 + Math.random() * 15)}`),
      600,
    )
  }, [emit])

  const handleExecuteIsolation = useCallback(async () => {
    const targets = data.nodes.filter((n) => n.kind === "flagged")
    if (targets.length === 0) return
    setIsolating(true)
    emit("containment", "TELEMETRY_LOG", `Computing Minimum-Cut boundary across ${targets.length} flagged accounts…`)
    const ids = targets.map((n) => n.id)
    const res = await executeContainment(ids, "Automated min-cut isolation of detected mule ring")
    const isolatedSet = new Set(res.isolated)
    setData((prev) => ({
      nodes: prev.nodes.map((n) =>
        isolatedSet.has(n.id) ? { ...n, kind: "frozen", status: "CONTAINED" } : n,
      ),
      links: prev.links,
    }))
    emit("containment", "CONTAINMENT_EXECUTION", `Min-Cut executed · ${res.isolated.length} accounts contained · source=${res.source}`)
    setIsolating(false)
    setSelected((cur) =>
      cur && isolatedSet.has(cur.id) ? { ...cur, kind: "frozen", status: "CONTAINED" } : cur,
    )
  }, [data.nodes, emit])

  const handleFreeze = useCallback(
    (node: GraphNode) => {
      setData((prev) => ({
        nodes: prev.nodes.map((n) => (n.id === node.id ? { ...n, kind: "frozen", status: "CONTAINED" } : n)),
        links: prev.links,
      }))
      setSelected((cur) => (cur && cur.id === node.id ? { ...cur, kind: "frozen", status: "CONTAINED" } : cur))
      emit("containment", "CONTAINMENT_EXECUTION", `Manual asset freeze applied to ${node.label}`)
    },
    [emit],
  )

  const runSar = useCallback(
    async (node: GraphNode) => {
      setSarOpen(true)
      setSarLoading(true)
      setSarReport(null)
      emit("compliance", "TELEMETRY_LOG", `Gemini drafting SAR narrative for ${node.label}…`)
      const report = await generateSar({
        accountId: node.id,
        riskScore: node.riskScore,
        shapDrivers: node.shap.map((s) => s.feature),
        detectedTopology: "cyclic micro-layering transaction ring",
      })
      setSarReport(report)
      setSarLoading(false)
      emit("compliance", "TELEMETRY_LOG", `SAR narrative complete · source=${report.source}`)
    },
    [emit],
  )

  const handleGlobalSar = useCallback(() => {
    const critical =
      [...data.nodes].filter((n) => n.kind === "flagged").sort((a, b) => b.riskScore - a.riskScore)[0] ??
      [...data.nodes].sort((a, b) => b.riskScore - a.riskScore)[0]
    if (critical) runSar(critical)
  }, [data.nodes, runSar])

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <NavBar />

      <main className="flex-1 px-4 py-4 md:px-6">
        <KpiCards nodeCount={data.nodes.length} edgeCount={data.links.length} />

        <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[1fr_380px]">
          {/* Graph + controls */}
          <section className="relative">
            <div className="scanline-grid glass-panel relative h-[560px] overflow-hidden rounded-xl xl:h-[calc(100vh-13rem)]">
              <GraphCanvas data={data} paused={paused} speed={speed} onNodeClick={setSelected} />

              <div className="pointer-events-none absolute left-3 top-3 flex flex-col gap-1.5">
                <Legend />
              </div>

              <div className="absolute inset-x-3 bottom-3">
                <ControlPanel
                  paused={paused}
                  onTogglePause={() => setPaused(!paused)}
                  speed={speed}
                  onSpeedChange={setSpeed}
                  onTriggerAttack={handleTriggerAttack}
                  onExecuteIsolation={handleExecuteIsolation}
                  onGenerateSar={handleGlobalSar}
                  isolating={isolating}
                  flaggedCount={flaggedNodes.length}
                />
              </div>
            </div>
          </section>

          {/* Telemetry */}
          <aside className="h-[420px] xl:h-[calc(100vh-13rem)]">
            <TelemetrySidebar events={events} state={state} />
          </aside>
        </div>
      </main>

      <NodeInspector
        node={selected}
        neighborCount={selected ? neighborCount(selected.id) : 0}
        onClose={() => setSelected(null)}
        onFreeze={handleFreeze}
        onGenerateSar={runSar}
      />

      <SarModal open={sarOpen} loading={sarLoading} report={sarReport} onClose={() => setSarOpen(false)} />
    </div>
  )
}

function Legend() {
  const items = [
    { label: "Clean", color: "var(--color-node-clean)" },
    { label: "Flagged / Mule", color: "var(--color-node-flagged)" },
    { label: "Frozen / Isolated", color: "var(--color-node-frozen)" },
  ]
  return (
    <div className="glass-panel rounded-lg px-3 py-2">
      <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Node States</p>
      <div className="flex flex-col gap-1">
        {items.map((i) => (
          <div key={i.label} className="flex items-center gap-2 text-xs text-foreground">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: i.color, boxShadow: `0 0 6px ${i.color}` }}
            />
            {i.label}
          </div>
        ))}
      </div>
    </div>
  )
}
