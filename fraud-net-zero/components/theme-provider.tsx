"use client"

import { createContext, useContext, useEffect, useState, useCallback } from "react"

type Theme = "dark" | "light"

type ThemeContextValue = {
  theme: Theme
  setTheme: (t: Theme) => void
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined)

const STORAGE_KEY = "fraudnet-theme"

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  // Default to the dark "command center" theme.
  const [theme, setThemeState] = useState<Theme>("dark")
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    const stored = (typeof window !== "undefined" &&
      window.localStorage.getItem(STORAGE_KEY)) as Theme | null
    if (stored === "light" || stored === "dark") {
      setThemeState(stored)
    }
    setMounted(true)
  }, [])

  useEffect(() => {
    const root = document.documentElement
    root.classList.remove(theme === "dark" ? "light" : "dark")
    root.classList.add(theme)
    if (mounted) {
      window.localStorage.setItem(STORAGE_KEY, theme)
    }
  }, [theme, mounted])

  const setTheme = useCallback((t: Theme) => setThemeState(t), [])
  const toggleTheme = useCallback(
    () => setThemeState((prev) => (prev === "dark" ? "light" : "dark")),
    [],
  )

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider")
  return ctx
}
