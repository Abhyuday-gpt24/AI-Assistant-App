"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useSyncExternalStore,
} from "react";

export type ThemePreference = "system" | "light" | "dark";
export type ResolvedTheme = "light" | "dark";

type ThemeContextValue = {
  theme: ThemePreference;
  resolvedTheme: ResolvedTheme;
  setTheme: (next: ThemePreference) => void;
  toggleTheme: () => void;
};

const STORAGE_KEY = "theme";
// Same-tab notification: setTheme writes localStorage then dispatches this so the
// external-store snapshots re-read (the native `storage` event only fires in
// OTHER tabs). Cross-tab sync still rides the native `storage` event.
const THEME_EVENT = "theme:changed";
const ThemeContext = createContext<ThemeContextValue | null>(null);

function getSystemTheme(): ResolvedTheme {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function readStoredTheme(): ThemePreference {
  if (typeof window === "undefined") return "system";
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (raw === "light" || raw === "dark") return raw;
  return "system";
}

function applyTheme(resolved: ResolvedTheme) {
  const root = document.documentElement;
  root.classList.toggle("dark", resolved === "dark");
  root.style.colorScheme = resolved;
}

// ── External store: the theme preference + the resolved theme are browser-only
// (localStorage + matchMedia). Reading them via useSyncExternalStore (the same
// approach as AuthProvider) is hydration-safe — the server snapshot is the
// neutral default, the client reads the real value after hydration WITHOUT a
// mismatch and WITHOUT a setState-in-effect. Subscribers fire on cross-tab
// `storage`, same-tab `theme:changed`, and (for resolved) system-scheme changes.

function subscribePreference(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener(THEME_EVENT, callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(THEME_EVENT, callback);
  };
}

function subscribeResolved(callback: () => void) {
  const mql = window.matchMedia("(prefers-color-scheme: dark)");
  window.addEventListener("storage", callback);
  window.addEventListener(THEME_EVENT, callback);
  mql.addEventListener("change", callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(THEME_EVENT, callback);
    mql.removeEventListener("change", callback);
  };
}

function getResolvedSnapshot(): ResolvedTheme {
  const pref = readStoredTheme();
  return pref === "system" ? getSystemTheme() : pref;
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  // Snapshots return primitives, so React's Object.is comparison is stable.
  const theme = useSyncExternalStore(
    subscribePreference,
    readStoredTheme,
    () => "system" as ThemePreference,
  );
  const resolvedTheme = useSyncExternalStore(
    subscribeResolved,
    getResolvedSnapshot,
    () => "light" as ResolvedTheme,
  );

  // Reflect the resolved theme onto <html>. A DOM side-effect (the legitimate use
  // of an effect) — no setState here, so no cascading render. The inline
  // ThemeScript already set the class pre-hydration; this keeps it in sync on
  // later changes (toggle / system switch).
  useEffect(() => {
    applyTheme(resolvedTheme);
  }, [resolvedTheme]);

  const setTheme = useCallback((next: ThemePreference) => {
    if (next === "system") {
      window.localStorage.removeItem(STORAGE_KEY);
    } else {
      window.localStorage.setItem(STORAGE_KEY, next);
    }
    // Notify the external store (same tab) → snapshots re-read → re-render.
    window.dispatchEvent(new Event(THEME_EVENT));
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme(resolvedTheme === "dark" ? "light" : "dark");
  }, [resolvedTheme, setTheme]);

  const value = useMemo<ThemeContextValue>(
    () => ({ theme, resolvedTheme, setTheme, toggleTheme }),
    [theme, resolvedTheme, setTheme, toggleTheme],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used inside <ThemeProvider>");
  }
  return ctx;
}
