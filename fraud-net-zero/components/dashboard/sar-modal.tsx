"use client"

import { useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import { X, FileText, Copy, Download, Check, Loader2, Sparkles } from "lucide-react"
import type { SarReport } from "@/lib/types"
import { shortId } from "@/lib/mock-data"

type Props = {
  open: boolean
  loading: boolean
  report: SarReport | null
  onClose: () => void
}

const SECTIONS = [
  { key: "executiveSummary", title: "1. Executive Summary" },
  { key: "typologyAnalysis", title: "2. Graph Typology & Transaction Pattern Analysis" },
  { key: "mitigation", title: "3. Recommended Regulatory Mitigation & Asset Freeze Action" },
] as const

function reportToText(report: SarReport) {
  return [
    "FinCEN SUSPICIOUS ACTIVITY REPORT (SAR)",
    `Subject Account: ${report.accountId}`,
    `Generated: ${new Date(report.generatedAt).toISOString()}`,
    `Source: ${report.source}`,
    "",
    ...SECTIONS.flatMap((s) => [s.title, report[s.key], ""]),
  ].join("\n")
}

export function SarModal({ open, loading, report, onClose }: Props) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    if (!report) return
    try {
      await navigator.clipboard.writeText(reportToText(report))
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {}
  }

  const handleExport = () => {
    if (!report) return
    const blob = new Blob([reportToText(report)], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `SAR_${report.accountId.slice(0, 12)}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-background/70 backdrop-blur-sm"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.94, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8 }}
            transition={{ type: "spring", stiffness: 300, damping: 28 }}
            className="relative flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-border bg-popover text-popover-foreground shadow-2xl"
          >
            <div className="flex items-center justify-between border-b border-border px-6 py-4">
              <div className="flex items-center gap-2.5">
                <span
                  className="flex h-9 w-9 items-center justify-center rounded-lg"
                  style={{
                    color: "var(--color-agent-compliance)",
                    backgroundColor: "color-mix(in srgb, var(--color-agent-compliance) 15%, transparent)",
                  }}
                >
                  <FileText className="h-5 w-5" />
                </span>
                <div>
                  <h2 className="text-sm font-semibold">FinCEN Suspicious Activity Report</h2>
                  <p className="text-xs text-muted-foreground">Gemini Compliance Agent</p>
                </div>
              </div>
              <button
                type="button"
                onClick={onClose}
                aria-label="Close report"
                className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="no-scrollbar flex-1 overflow-y-auto px-6 py-5">
              {loading || !report ? (
                <div className="flex flex-col items-center justify-center gap-3 py-16 text-muted-foreground">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                  <p className="text-sm">Drafting SAR narrative…</p>
                </div>
              ) : (
                <div className="space-y-5">
                  <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-muted/40 px-3 py-2 text-xs">
                    <span className="font-mono text-muted-foreground">Subject: {shortId(report.accountId)}</span>
                    <span
                      className="ml-auto flex items-center gap-1 rounded-full px-2 py-0.5 font-medium"
                      style={{
                        color: report.source === "gemini-api" ? "var(--color-agent-compliance)" : "var(--color-warning)",
                        backgroundColor: `color-mix(in srgb, ${report.source === "gemini-api" ? "var(--color-agent-compliance)" : "var(--color-warning)"} 14%, transparent)`,
                      }}
                    >
                      <Sparkles className="h-3 w-3" />
                      {report.source}
                    </span>
                  </div>
                  {SECTIONS.map((s) => (
                    <section key={s.key}>
                      <h3 className="mb-1.5 text-sm font-semibold text-foreground">{s.title}</h3>
                      <p className="text-sm leading-relaxed text-muted-foreground">{report[s.key]}</p>
                    </section>
                  ))}
                </div>
              )}
            </div>

            <div className="flex gap-2 border-t border-border px-6 py-4">
              <button
                type="button"
                onClick={handleCopy}
                disabled={!report}
                className="flex items-center gap-2 rounded-lg border border-border bg-muted px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent disabled:opacity-40"
              >
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                {copied ? "Copied" : "Copy Report"}
              </button>
              <button
                type="button"
                onClick={handleExport}
                disabled={!report}
                className="ml-auto flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-40"
              >
                <Download className="h-4 w-4" />
                Export SAR PDF
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
