"use client";

import {
  useEffect,
  useRef,
  type ChangeEvent,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import {
  CloseIcon,
  FileIcon,
  PaperclipIcon,
  SendIcon,
  SpinnerIcon,
} from "@/components/ui/icons";
import { ALLOWED_UPLOAD_TYPES } from "@/lib/api/uploads";

export type AttachedFile = {
  id: string;
  name: string;
  status: "uploading" | "uploaded" | "error";
  // RAG indexing state for documents, once uploaded.
  ingestStatus?: "indexing" | "ready" | "error";
  error?: string;
};

type ChatboxProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  attachments: AttachedFile[];
  onAddFiles: (files: File[]) => void;
  onRemoveAttachment: (id: string) => void;
};

export function Chatbox({
  value,
  onChange,
  onSubmit,
  disabled,
  attachments,
  onAddFiles,
  onRemoveAttachment,
}: ChatboxProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 240)}px`;
  }, [value]);

  // Block sending while any attachment is still uploading — its storage_path
  // isn't known yet, so it couldn't be included in the message.
  const uploading = attachments.some((a) => a.status === "uploading");
  const hasReadyAttachment = attachments.some((a) => a.status === "uploaded");
  const canSend = (value.trim().length > 0 || hasReadyAttachment) && !uploading;

  function submit() {
    if (!canSend || disabled) return;
    onSubmit();
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submit();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  function handleFilesPicked(event: ChangeEvent<HTMLInputElement>) {
    const files = event.target.files ? Array.from(event.target.files) : [];
    if (files.length > 0) onAddFiles(files);
    // Reset so picking the same file again still fires onChange.
    event.target.value = "";
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mx-auto w-full max-w-4xl px-3 pb-3 pt-2 sm:px-4"
    >
      <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-2 shadow-sm focus-within:border-[var(--ring)] focus-within:ring-2 focus-within:ring-[var(--ring)]/30">
        {attachments.length > 0 && (
          <ul className="mb-2 flex flex-wrap gap-2 px-1">
            {attachments.map((file) => (
              <li
                key={file.id}
                className="flex max-w-[220px] items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--muted)] px-2 py-1 text-xs text-[var(--foreground)]"
              >
                {file.status === "uploading" ? (
                  <SpinnerIcon className="h-3.5 w-3.5 shrink-0 animate-spin text-[var(--muted-foreground)]" />
                ) : (
                  <FileIcon
                    className={
                      file.status === "error"
                        ? "h-3.5 w-3.5 shrink-0 text-red-500"
                        : "h-3.5 w-3.5 shrink-0 text-[var(--muted-foreground)]"
                    }
                  />
                )}
                <span className="truncate" title={file.error ?? file.name}>
                  {file.name}
                </span>
                {file.status === "error" && (
                  <span className="shrink-0 text-red-500">failed</span>
                )}
                {file.status === "uploaded" && file.ingestStatus === "indexing" && (
                  <span className="flex shrink-0 items-center gap-1 text-[var(--muted-foreground)]">
                    <SpinnerIcon className="h-3 w-3 animate-spin" />
                    indexing
                  </span>
                )}
                {file.status === "uploaded" && file.ingestStatus === "ready" && (
                  <span className="shrink-0 text-[var(--muted-foreground)]">indexed</span>
                )}
                {file.status === "uploaded" && file.ingestStatus === "error" && (
                  <span className="shrink-0 text-red-500" title={file.error}>
                    index failed
                  </span>
                )}
                <button
                  type="button"
                  onClick={() => onRemoveAttachment(file.id)}
                  aria-label={`Remove ${file.name}`}
                  className="ml-0.5 inline-flex h-4 w-4 shrink-0 items-center justify-center rounded text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                >
                  <CloseIcon className="h-3 w-3" />
                </button>
              </li>
            ))}
          </ul>
        )}

        <div className="flex items-end gap-2">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept={ALLOWED_UPLOAD_TYPES.join(",")}
            onChange={handleFilesPicked}
            className="hidden"
            tabIndex={-1}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
            aria-label="Attach file"
            title="Attach file"
            className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-[var(--muted-foreground)] transition-colors hover:bg-[var(--muted)] hover:text-[var(--foreground)] disabled:opacity-40"
          >
            <PaperclipIcon className="h-5 w-5" />
          </button>
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
            disabled={!canSend || disabled}
            aria-label="Send message"
            className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--primary)] text-[var(--primary-foreground)] transition-opacity hover:opacity-90 disabled:opacity-40"
          >
            <SendIcon className="h-5 w-5" />
          </button>
        </div>
      </div>
      <p className="mt-2 text-center text-[11px] text-[var(--muted-foreground)]">
        Press <kbd className="rounded border border-[var(--border)] px-1">Enter</kbd>{" "}
        to send, <kbd className="rounded border border-[var(--border)] px-1">Shift</kbd>+
        <kbd className="rounded border border-[var(--border)] px-1">Enter</kbd> for new line.
      </p>
    </form>
  );
}
