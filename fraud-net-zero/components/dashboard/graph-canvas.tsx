"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import dynamic from "next/dynamic"
import type { GraphData, GraphNode } from "@/lib/types"
import { useTheme } from "@/components/theme-provider"

const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center text-sm text-muted-foreground">
      Initializing 3D graph engine…
    </div>
  ),
})

type Palette = {
  bg: string
  clean: string
  flagged: string
  frozen: string
  edge: string
  particle: string
}

const PALETTES: Record<"dark" | "light", Palette> = {
  dark: {
    bg: "#090d16",
    clean: "#34d399",
    flagged: "#ef4444",
    frozen: "#64748b",
    edge: "#26334a",
    particle: "#22d3ee",
  },
  light: {
    bg: "#f1f5f9",
    clean: "#059669",
    flagged: "#dc2626",
    frozen: "#94a3b8",
    edge: "#cbd5e1",
    particle: "#0891b2",
  },
}

type Props = {
  data: GraphData
  paused: boolean
  speed: number
  onNodeClick: (node: GraphNode) => void
}

export function GraphCanvas({ data, paused, speed, onNodeClick }: Props) {
  const { theme } = useTheme()
  const palette = PALETTES[theme]
  const containerRef = useRef<HTMLDivElement>(null)
  const fgRef = useRef<any>(null)
  const [size, setSize] = useState({ w: 0, h: 0 })

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const ro = new ResizeObserver((entries) => {
      const rect = entries[0].contentRect
      setSize({ w: Math.floor(rect.width), h: Math.floor(rect.height) })
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const nodeColor = useMemo(
    () => (node: any) => {
      const n = node as GraphNode
      if (n.kind === "frozen") return palette.frozen
      if (n.kind === "flagged") return palette.flagged
      return palette.clean
    },
    [palette],
  )

  // Refresh colors + charge on theme change.
  useEffect(() => {
    if (fgRef.current) {
      fgRef.current.refresh?.()
    }
  }, [theme])

  const particleSpeed = paused ? 0 : 0.004 * speed + 0.002

  return (
    <div ref={containerRef} className="relative h-full w-full overflow-hidden">
      {size.w > 0 && (
        <ForceGraph3D
          ref={fgRef}
          width={size.w}
          height={size.h}
          graphData={data}
          backgroundColor={palette.bg}
          showNavInfo={false}
          nodeLabel={(n: any) =>
            `<div style="font-family:monospace;font-size:11px;padding:2px 4px">${(n as GraphNode).label} · risk ${(n as GraphNode).riskScore}</div>`
          }
          nodeColor={nodeColor}
          nodeOpacity={theme === "dark" ? 0.92 : 1}
          nodeVal={(n: any) => 1.5 + (n as GraphNode).riskScore / 22}
          nodeResolution={12}
          linkColor={() => palette.edge}
          linkWidth={0.6}
          linkOpacity={theme === "dark" ? 0.45 : 0.6}
          linkDirectionalParticles={(l: any) => Math.min(4, Math.ceil((l.value ?? 1) / 3))}
          linkDirectionalParticleWidth={2.2}
          linkDirectionalParticleSpeed={particleSpeed}
          linkDirectionalParticleColor={() => palette.particle}
          onNodeClick={(n: any) => onNodeClick(n as GraphNode)}
          cooldownTicks={120}
          warmupTicks={20}
        />
      )}
    </div>
  )
}
