"use client";

import { useState } from "react";
import { cn } from "@/lib/cn";
import type { ChatMessage } from "./types";

type CheckpointerProps = {
  messages: ChatMessage[];
  onJump: (messageId: string) => void;
  className?: string;
};

export function Checkpointer({ messages, onJump, className }: CheckpointerProps) {
  const [open, setOpen] = useState(false);
  const checkpoints = messages.filter((m) => m.role === "user");

  if (checkpoints.length === 0) return null;

  return (
    <div
      className={cn(
        "pointer-events-auto hidden md:flex flex-col items-end",
        className,
      )}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node)) {
          setOpen(false);
        }
      }}
      aria-label="Chat checkpoints"
    >
      <div
        className={cn(
          "flex flex-col overflow-hidden rounded-2xl border border-border bg-(--card)/95 shadow-sm backdrop-blur transition-all duration-200 ease-out",
          open
            ? "max-h-[70vh] w-64 overflow-y-auto p-2"
            : "max-h-[70vh] w-2 gap-1 p-1",
        )}
      >
        {open && (
          <div className="px-2 pb-2 pt-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            Checkpoints
          </div>
        )}
        {checkpoints.map((cp, index) => (
          <button
            key={cp.id}
            type="button"
            onClick={() => onJump(cp.id)}
            title={open ? undefined : cp.content}
            aria-label={`Jump to message ${index + 1}: ${cp.content}`}
            className={cn(
              "group block w-full text-left transition-colors",
              open
                ? "rounded-md px-2 py-2 text-xs text-foreground hover:bg-accent"
                : "h-1.5 shrink-0 rounded-full bg-(--muted-foreground)/40 hover:bg-foreground",
            )}
          >
            {open && (
              <div className="flex items-start gap-2">
                <span className="mt-0.5 inline-flex h-4 min-w-5 items-center justify-center rounded bg-muted px-1 text-[10px] font-medium text-muted-foreground">
                  {index + 1}
                </span>
                <span className="line-clamp-2 flex-1 leading-snug">
                  {cp.content}
                </span>
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
