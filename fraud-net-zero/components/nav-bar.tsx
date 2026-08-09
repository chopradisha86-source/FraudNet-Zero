"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { ShieldHalf, LayoutDashboard, Network, Settings, LogIn } from "lucide-react"
import { ThemeToggle } from "./theme-toggle"
import { ConnectionBadges } from "./connection-badges"

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/architecture", label: "Architecture", icon: Network },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/login", label: "Login", icon: LogIn },
]

export function NavBar() {
  const pathname = usePathname()

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border bg-background/80 backdrop-blur-xl">
      <div className="flex h-16 items-center gap-4 px-4 md:px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="relative flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground glow-primary">
            <ShieldHalf className="h-5 w-5" />
          </span>
          <span className="flex flex-col leading-none">
            <span className="text-sm font-semibold tracking-tight text-foreground">
              FraudNet<span className="text-primary">-Zero</span>
            </span>
            <span className="mt-0.5 text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Command Center
            </span>
          </span>
        </Link>

        <nav className="ml-4 hidden items-center gap-1 lg:flex">
          {NAV.map((item) => {
            const active = pathname === item.href
            const Icon = item.icon
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  active
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                }`}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            )
          })}
        </nav>

        <div className="ml-auto flex items-center gap-3">
          <ConnectionBadges />
          <ThemeToggle />
        </div>
      </div>
    </header>
  )
}
