"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { ShieldHalf, Loader2, Zap, Lock, User } from "lucide-react"
import { ThemeToggle } from "@/components/theme-toggle"
import { login } from "@/lib/api"

export default function LoginPage() {
  const router = useRouter()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [source, setSource] = useState<string | null>(null)

  const submit = async (u: string, p: string) => {
    setLoading(true)
    const res = await login(u, p)
    setSource(res.source)
    setTimeout(() => router.push("/"), 500)
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-4">
      <div className="scanline-grid pointer-events-none absolute inset-0 opacity-60" />
      <div className="absolute right-4 top-4">
        <ThemeToggle />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 18, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.45 }}
        className="glass-panel relative z-10 w-full max-w-md rounded-2xl p-8"
      >
        <div className="mb-6 flex flex-col items-center text-center">
          <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground glow-primary">
            <ShieldHalf className="h-7 w-7" />
          </span>
          <h1 className="mt-4 text-xl font-semibold tracking-tight text-foreground">
            FraudNet<span className="text-primary">-Zero</span>
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">Analyst authentication required</p>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault()
            submit(username || "analyst", password || "demo")
          }}
          className="space-y-4"
        >
          <Field
            icon={User}
            label="Analyst ID"
            value={username}
            onChange={setUsername}
            placeholder="analyst@fraudnet.io"
          />
          <Field
            icon={Lock}
            label="Passphrase"
            type="password"
            value={password}
            onChange={setPassword}
            placeholder="••••••••••"
          />

          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-60"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Lock className="h-4 w-4" />}
            Authenticate
          </button>
        </form>

        <div className="my-5 flex items-center gap-3">
          <span className="h-px flex-1 bg-border" />
          <span className="text-[10px] uppercase tracking-widest text-muted-foreground">or</span>
          <span className="h-px flex-1 bg-border" />
        </div>

        <button
          type="button"
          disabled={loading}
          onClick={() => submit("demo-analyst", "one-click")}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-border bg-muted px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:opacity-60"
        >
          <Zap className="h-4 w-4" style={{ color: "var(--color-warning)" }} />
          One-Click Demo Analyst Login
        </button>

        {source && (
          <p className="mt-4 text-center font-mono text-xs text-muted-foreground">
            Authenticated · token source: <span className="text-primary">{source}</span>
          </p>
        )}
      </motion.div>
    </div>
  )
}

function Field({
  icon: Icon,
  label,
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  icon: typeof User
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
  type?: string
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-muted-foreground">{label}</span>
      <span className="flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2.5 focus-within:border-primary focus-within:ring-1 focus-within:ring-ring">
        <Icon className="h-4 w-4 text-muted-foreground" />
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
        />
      </span>
    </label>
  )
}
