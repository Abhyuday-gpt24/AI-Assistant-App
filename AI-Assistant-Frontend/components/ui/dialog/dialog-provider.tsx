"use client";

import {
  createContext,
  useContext,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { AlertDialog, type DialogVariant } from "./alert-dialog";

type ConfirmOptions = {
  title?: string;
  message: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: DialogVariant;
};

type AlertOptions = {
  title?: string;
  message: ReactNode;
  confirmLabel?: string;
  variant?: DialogVariant;
};

type DialogContextValue = {
  /** Two-button modal. Resolves true on confirm, false on cancel/backdrop/Escape. */
  confirm: (options: ConfirmOptions) => Promise<boolean>;
  /** Single-button modal. Resolves once dismissed. */
  alert: (options: AlertOptions) => Promise<void>;
};

const DialogContext = createContext<DialogContextValue | null>(null);

type ActiveDialog = {
  mode: "confirm" | "alert";
  options: ConfirmOptions;
};

/**
 * App-wide modal dialog. Renders one shared <AlertDialog> and exposes an
 * imperative, promise-based API so any component can `await confirm(...)` /
 * `await alert(...)` instead of reaching for `window.confirm` / `window.alert`.
 * Mount once near the root; consume with `useDialog()`.
 */
export function DialogProvider({ children }: { children: ReactNode }) {
  const [active, setActive] = useState<ActiveDialog | null>(null);
  // Resolver for the promise of the currently-open dialog. Alerts wrap their
  // void resolver so the same (boolean) => void slot serves both modes.
  // (Plain functions / object below — the React Compiler memoizes them; manual
  // useCallback/useMemo here can't be preserved through compilation.)
  const resolverRef = useRef<((value: boolean) => void) | null>(null);

  const settle = (result: boolean) => {
    resolverRef.current?.(result);
    resolverRef.current = null;
    setActive(null);
  };

  const open = (dialog: ActiveDialog, resolve: (value: boolean) => void) => {
    // Settle any dialog still open (shouldn't normally happen) so its awaiter
    // isn't left hanging when a new one takes its place.
    resolverRef.current?.(false);
    resolverRef.current = resolve;
    setActive(dialog);
  };

  const confirm = (options: ConfirmOptions) =>
    new Promise<boolean>((resolve) => {
      open(
        {
          mode: "confirm",
          options: { confirmLabel: "Confirm", cancelLabel: "Cancel", ...options },
        },
        resolve,
      );
    });

  const alert = (options: AlertOptions) =>
    new Promise<void>((resolve) => {
      open(
        { mode: "alert", options: { confirmLabel: "OK", ...options } },
        () => resolve(),
      );
    });

  const value = { confirm, alert };

  return (
    <DialogContext.Provider value={value}>
      {children}
      <AlertDialog
        open={active !== null}
        title={active?.options.title}
        message={active?.options.message ?? ""}
        confirmLabel={active?.options.confirmLabel}
        cancelLabel={
          active?.mode === "confirm" ? active.options.cancelLabel : undefined
        }
        variant={active?.options.variant}
        onConfirm={() => settle(true)}
        onCancel={() => settle(false)}
      />
    </DialogContext.Provider>
  );
}

export function useDialog(): DialogContextValue {
  const ctx = useContext(DialogContext);
  if (!ctx) {
    throw new Error("useDialog must be used within a DialogProvider");
  }
  return ctx;
}
