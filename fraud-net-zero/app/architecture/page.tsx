"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import {
  Radio,
  Database,
  Search,
  Scale,
  Shield,
  FileText,
  ArrowRight,
  Server,
  Cpu,
} from "lucide-react"
import { NavBar } from "@/components/nav-bar"

type Stage = {
  id: string
  title: string
  subtitle: string
  icon: typeof Radio
  accent: string
  detail: string
  meta: string[]
}

const PIPELINE: Stage[] = [
  {
    id: "kafka",
    title: "Kafka Ingestion",
    subtitle: "Streaming transaction bus",
    icon: Radio,
    accent: "var(--color-agent-topology)",
    detail:
      "Raw settlement events are published to partitioned Kafka topics at up to 1.6K tx/s. Each event is normalized, deduplicated, and enriched with counterparty metadata before entering the graph store.",
    meta: ["Topic: tx.settlement.v2", "Throughput: 1.6K tx/s", "Exactly-once semantics"],
  },
  {
    id: "memgraph",
    title: "Memgraph Store",
    subtitle: "Real-time property graph",
    icon: Database,
    accent: "var(--color-agent-compliance)",
    detail:
      "A streaming in-memory graph maintains accounts as nodes and transfers as directed, weighted edges. Cypher triggers fire incremental topology recomputation as edges arrive.",
    meta: ["12,450 nodes · 48,210 edges", "Incremental Louvain", "MAGE algorithms"],
  },
  {
    id: "agents",
    title: "Multi-Agent Pipeline",
    subtitle: "Detection & response",
    icon: Cpu,
    accent: "var(--color-primary)",
    detail:
      "Four cooperating agents observe the live graph, score anomalies, compute containment boundaries, and draft regulatory narratives — coordinating over a shared telemetry bus.",
    meta: ["4 autonomous agents", "WebSocket telemetry", "Sub-100ms inference"],
  },
]

const AGENTS = [
  {
    icon: Search,
    title: "Topology Agent",
    accent: "var(--color-agent-topology)",
    desc: "Detects cyclic micro-layering loops and maintains Louvain community partitions.",
  },
  {
    icon: Scale,
    title: "Risk Scoring Agent",
    accent: "var(--color-agent-risk)",
    desc: "GCN + XGBoost ensemble scoring anomalies with SHAP feature attribution.",
  },
  {
    icon: Shield,
    title: "Automated Containment Agent",
    accent: "var(--color-agent-containment)",
    desc: "Computes Minimum-Cut isolation boundaries to sever mule accounts.",
  },
  {
    icon: FileText,
    title: "Gemini Compliance Agent",
    accent: "var(--color-agent-compliance)",
    desc: "Drafts formal FinCEN SAR narratives with graph-typology evidence.",
  },
]

export default function ArchitecturePage() {
  const [active, setActive] = useState<string>("kafka")
  const activeStage = PIPELINE.find((s) => s.id === active)!

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <NavBar />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 md:px-6">
        <div className="flex items-center gap-2 text-primary">
          <Server className="h-4 w-4" />
          <span className="font-mono text-xs uppercase tracking-widest">System Design</span>
        </div>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-foreground text-balance">
          Real-Time Detection Architecture
        </h1>
        <p className="mt-2 max-w-2xl text-muted-foreground text-pretty">
          FraudNet-Zero streams settlement data through a graph-native pipeline. Explore each stage from ingestion to
          automated regulatory response.
        </p>

        {/* Pipeline flow */}
        <div className="mt-8 flex flex-col items-stretch gap-3 md:flex-row md:items-center">
          {PIPELINE.map((stage, i) => (
            <div key={stage.id} className="flex flex-1 items-center gap-3">
              <button
                type="button"
                onClick={() => setActive(stage.id)}
                className={`glass-panel flex w-full flex-col gap-2 rounded-xl p-4 text-left transition-all ${
                  active === stage.id ? "ring-1 ring-primary" : "opacity-70 hover:opacity-100"
                }`}
              >
                <span
                  className="flex h-10 w-10 items-center justify-center rounded-lg"
                  style={{ backgroundColor: `color-mix(in srgb, ${stage.accent} 16%, transparent)`, color: stage.accent }}
                >
                  <stage.icon className="h-5 w-5" />
                </span>
                <span className="text-sm font-semibold text-foreground">{stage.title}</span>
                <span className="text-xs text-muted-foreground">{stage.subtitle}</span>
              </button>
              {i < PIPELINE.length - 1 && (
                <ArrowRight className="hidden h-5 w-5 shrink-0 text-muted-foreground md:block" />
              )}
            </div>
          ))}
        </div>

        {/* Active stage detail */}
        <motion.div
          key={activeStage.id}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel mt-4 rounded-xl p-6"
        >
          <div className="flex items-center gap-2">
            <activeStage.icon className="h-5 w-5" style={{ color: activeStage.accent }} />
            <h2 className="text-lg font-semibold text-foreground">{activeStage.title}</h2>
          </div>
          <p className="mt-2 max-w-3xl leading-relaxed text-muted-foreground">{activeStage.detail}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {activeStage.meta.map((m) => (
              <span
                key={m}
                className="rounded-full border border-border bg-muted px-3 py-1 font-mono text-xs text-muted-foreground"
              >
                {m}
              </span>
            ))}
          </div>
        </motion.div>

        {/* Agents grid */}
        <h2 className="mt-10 text-lg font-semibold text-foreground">The Multi-Agent Pipeline</h2>
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {AGENTS.map((a, i) => (
            <motion.div
              key={a.title}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
              className="glass-panel flex gap-4 rounded-xl p-5"
            >
              <span
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg"
                style={{ backgroundColor: `color-mix(in srgb, ${a.accent} 16%, transparent)`, color: a.accent }}
              >
                <a.icon className="h-5 w-5" />
              </span>
              <div>
                <h3 className="text-sm font-semibold text-foreground">{a.title}</h3>
                <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{a.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </main>
    </div>
  )
}
