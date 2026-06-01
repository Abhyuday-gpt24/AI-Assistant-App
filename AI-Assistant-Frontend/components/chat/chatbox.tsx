"use client";

import { useEffect, useRef, type FormEvent, type KeyboardEvent } from "react";
import { SendIcon } from "@/components/ui/icons";

type ChatboxProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
};

export function Chatbox({ value, onChange, onSubmit, disabled }: ChatboxProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 240)}px`;
  }, [value]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!value.trim() || disabled) return;
    onSubmit();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!value.trim() || disabled) return;
      onSubmit();
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mx-auto w-full max-w-4xl px-3 pb-3 pt-2 sm:px-4"
    >
      <div className="flex items-end gap-2 rounded-2xl border border-[var(--border)] bg-[var(--card)] p-2 shadow-sm focus-within:border-[var(--ring)] focus-within:ring-2 focus-within:ring-[var(--ring)]/30">
        <textarea
          ref={textareaRef}
          rows={1}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Message AI Doc Assist..."
          disabled={disabled}
          className="block max-h-60 min-h-[52px] w-full resize-none bg-transparent px-2 py-2.5 text-base leading-relaxed text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!value.trim() || disabled}
          aria-label="Send message"
          className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--primary)] text-[var(--primary-foreground)] transition-opacity hover:opacity-90 disabled:opacity-40"
        >
          <SendIcon className="h-5 w-5" />
        </button>
      </div>
      <p className="mt-2 text-center text-[11px] text-[var(--muted-foreground)]">
        Press <kbd className="rounded border border-[var(--border)] px-1">Enter</kbd>{" "}
        to send, <kbd className="rounded border border-[var(--border)] px-1">Shift</kbd>+
        <kbd className="rounded border border-[var(--border)] px-1">Enter</kbd> for new line.
      </p>
    </form>
  );
}
