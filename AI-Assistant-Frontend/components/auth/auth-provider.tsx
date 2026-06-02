"use client";

import {
  createContext,
  useCallback,
  useContext,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import type { User } from "@/lib/api/auth";

const STORAGE_KEY = "auth_user";

type AuthContextValue = {
  user: User | null;
  setUser: (user: User | null) => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

// --- localStorage-backed auth-profile store ---------------------------------
// The httpOnly auth cookie isn't readable from JS, so we cache the user profile
// in localStorage purely so the UI can show the name after a refresh. It's read
// via useSyncExternalStore (NOT a mount effect) so it is:
//   - hydration-safe: the server snapshot is always null, matching SSR, so there
//     is no hydration mismatch (the client updates after hydration), and
//   - lint-clean: no setState inside an effect (the cascading-render anti-pattern).
// `currentUser` is the in-memory source of truth, so the UI still works if
// localStorage is unavailable; storage is just persistence + cross-tab sync.

let currentUser: User | null = null;
let initialized = false;
const listeners = new Set<() => void>();

function parseStored(): User | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as User;
    if (parsed && typeof parsed.id !== "undefined" && parsed.name) {
      return parsed;
    }
  } catch {
    // missing / malformed / disabled storage → no cached profile
  }
  return null;
}

// Stable reference between changes: useSyncExternalStore compares snapshots with
// Object.is, so we must NOT parse a fresh object on every call.
function getSnapshot(): User | null {
  if (!initialized) {
    initialized = true;
    currentUser = parseStored();
  }
  return currentUser;
}

function subscribe(callback: () => void): () => void {
  listeners.add(callback);
  // Cross-tab updates: another tab writing the profile fires a `storage` event.
  const onStorage = (e: StorageEvent) => {
    if (e.key !== null && e.key !== STORAGE_KEY) return;
    currentUser = parseStored();
    callback();
  };
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(callback);
    window.removeEventListener("storage", onStorage);
  };
}

function writeUser(next: User | null): void {
  currentUser = next; // in-memory truth first, so the UI updates even if storage throws
  try {
    if (next) {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } else {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    // storage may be disabled; in-memory state still works
  }
  for (const notify of listeners) notify();
}

export function AuthProvider({ children }: { children: ReactNode }) {
  // getServerSnapshot (3rd arg) returns null so SSR + first client render agree.
  const user = useSyncExternalStore(subscribe, getSnapshot, () => null);

  const setUser = useCallback((next: User | null) => {
    writeUser(next);
  }, []);

  return (
    <AuthContext.Provider value={{ user, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}
