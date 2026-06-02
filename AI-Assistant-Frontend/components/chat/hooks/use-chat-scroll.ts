import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatMessage } from "../types";

// Owns the scroll container: auto-sticks to the bottom as messages change, and
// exposes jumpTo() (used by the Checkpointer) which smooth-scrolls to a message
// and briefly flashes it.
export function useChatScroll(messages: ChatMessage[]) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [flashId, setFlashId] = useState<string | null>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages]);

  const jumpTo = useCallback((messageId: string) => {
    const container = scrollRef.current;
    if (!container) return;
    const target = container.querySelector<HTMLElement>(
      `[data-message-id="${messageId}"]`,
    );
    if (!target) return;
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    setFlashId(messageId);
    window.setTimeout(() => {
      setFlashId((current) => (current === messageId ? null : current));
    }, 1200);
  }, []);

  return { scrollRef, flashId, jumpTo };
}
