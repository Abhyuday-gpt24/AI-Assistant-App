"use client";

import { useEffect, useId, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createProject, type Project } from "@/lib/api/projects";
import { emitProjectsChanged } from "@/lib/events";
import { errorMessage } from "@/lib/api/error-message";

type NewProjectDialogProps = {
  open: boolean;
  onClose: () => void;
  /** Fired with the created project so the opener can navigate to it. */
  onCreated?: (project: Project) => void;
};

/**
 * Create-project modal: name (required) + description. On submit it POSTs to the
 * backend (which generates the project id used as the shared RAG namespace),
 * announces the change so lists refresh, and hands the new project back to the
 * opener. Overlay/card styling mirrors the app's AlertDialog; it's a standalone
 * form modal because the shared dialog is confirm/alert-only (no inputs).
 */
export function NewProjectDialog({
  open,
  onClose,
  onCreated,
}: NewProjectDialogProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const nameRef = useRef<HTMLInputElement>(null);
  const titleId = useId();
  const nameId = useId();
  const descId = useId();

  // Reset the form when the modal transitions to open — done DURING render (the
  // React-recommended alternative to a prop-syncing effect; avoids the
  // set-state-in-effect lint rule). The effect below handles only external
  // concerns (focus + Escape), which don't setState synchronously.
  const [wasOpen, setWasOpen] = useState(open);
  if (open !== wasOpen) {
    setWasOpen(open);
    if (open) {
      setName("");
      setDescription("");
      setError(null);
      setSubmitting(false);
    }
  }

  // Focus the name field when the modal opens and close on Escape.
  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    nameRef.current?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      previouslyFocused?.focus?.();
    };
  }, [open, onClose]);

  if (!open) return null;

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const project = await createProject(trimmed, description.trim());
      emitProjectsChanged();
      onCreated?.(project);
      onClose();
    } catch (err) {
      setError(errorMessage(err, "Couldn't create the project. Please try again."));
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/50 transition-opacity"
        onClick={onClose}
        aria-hidden
      />

      <form
        onSubmit={handleSubmit}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="relative w-full max-w-md rounded-lg border border-[var(--border)] bg-[var(--card)] p-5 text-[var(--card-foreground)] shadow-xl"
      >
        <h2 id={titleId} className="text-base font-semibold">
          New project
        </h2>
        <p className="mt-1 text-sm text-[var(--muted-foreground)]">
          Group related chats so they share one set of uploaded documents.
        </p>

        <div className="mt-4 space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor={nameId}>Name</Label>
            <Input
              ref={nameRef}
              id={nameId}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Q2 Research"
              maxLength={120}
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor={descId}>Description</Label>
            <textarea
              id={descId}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is this project about? (optional)"
              rows={3}
              maxLength={500}
              className="block w-full resize-none rounded-md border border-[var(--input)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]/40"
            />
          </div>
        </div>

        {error && (
          <p role="alert" className="mt-3 text-sm text-red-500">
            {error}
          </p>
        )}

        <div className="mt-5 flex justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onClose}
            disabled={submitting}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            size="sm"
            disabled={submitting || name.trim().length === 0}
          >
            {submitting ? "Creating…" : "Create project"}
          </Button>
        </div>
      </form>
    </div>
  );
}
