"use client";

import { useEffect, useId, useRef, type ReactNode } from "react";
import { Button } from "@/components/ui/button";

export type DialogVariant = "default" | "danger";

export type AlertDialogProps = {
  open: boolean;
  title?: string;
  message: ReactNode;
  confirmLabel?: string;
  /** Omit for a single-button "alert" (no cancel / dismiss action). */
  cancelLabel?: string;
  variant?: DialogVariant;
  onConfirm: () => void;
  /** Fired by the Cancel button, backdrop click, and the Escape key. */
  onCancel: () => void;
};

/**
 * Presentational modal — pure props, no business logic. It renders an overlay +
 * centered card and reports intent through `onConfirm` / `onCancel`. The
 * imperative, promise-based wrapper lives in `DialogProvider`; use that (via
 * `useDialog()`) rather than wiring this up by hand.
 */
export function AlertDialog({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel,
  variant = "default",
  onConfirm,
  onCancel,
}: AlertDialogProps) {
  const confirmRef = useRef<HTMLButtonElement>(null);
  const titleId = useId();
  const messageId = useId();

  // While open: focus the confirm button, close on Escape, and restore focus to
  // whatever was focused before (e.g. the trash button) when it closes.
  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    confirmRef.current?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onCancel();
      }
    };
    document.addEventListener("keydown", onKeyDown);

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      previouslyFocused?.focus?.();
    };
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/50 transition-opacity"
        onClick={onCancel}
        aria-hidden
      />

      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
        aria-describedby={messageId}
        className="relative w-full max-w-sm rounded-lg border border-[var(--border)] bg-[var(--card)] p-5 text-[var(--card-foreground)] shadow-xl"
      >
        {title && (
          <h2 id={titleId} className="text-base font-semibold">
            {title}
          </h2>
        )}
        <div
          id={messageId}
          className="mt-2 text-sm text-[var(--muted-foreground)]"
        >
          {message}
        </div>

        <div className="mt-5 flex justify-end gap-2">
          {cancelLabel && (
            <Button variant="outline" size="sm" onClick={onCancel}>
              {cancelLabel}
            </Button>
          )}
          <Button
            ref={confirmRef}
            variant={variant === "danger" ? "danger" : "primary"}
            size="sm"
            onClick={onConfirm}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
