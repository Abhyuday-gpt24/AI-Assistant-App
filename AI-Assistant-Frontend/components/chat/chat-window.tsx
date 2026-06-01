"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Chatbox } from "./chatbox";
import { Checkpointer } from "./checkpointer";
import { MessageIcon, UserIcon } from "@/components/ui/icons";
import { MessageContent } from "./message-content";
import { cn } from "@/lib/cn";
import type { ChatMessage } from "./types";
import { ApiError } from "@/lib/api/client";
import { streamChat } from "@/lib/api/chat";
import { getChats, getMessages, type MessageItem } from "@/lib/api/chats";

type ChatWindowProps = {
  title: string;
  subtitle?: string;
  chatId?: string;
};

function toChatMessage(m: MessageItem, index: number): ChatMessage {
  return {
    id: `h-${index}-${m.created_at}`,
    role: m.role === "user" ? "user" : "assistant",
    content: m.content,
    createdAt: m.created_at,
  };
}

export function ChatWindow({
  title,
  subtitle,
  chatId: initialChatId,
}: ChatWindowProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(
    Boolean(initialChatId),
  );
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [flashId, setFlashId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const chatIdRef = useRef<string | undefined>(initialChatId);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!initialChatId) return;
    let cancelled = false;
    setLoadingHistory(true);
    setHistoryError(null);
    getMessages(initialChatId)
      .then((items) => {
        if (cancelled) return;
        setMessages(items.map(toChatMessage));
      })
      .catch((err) => {
        if (cancelled) return;
        const message =
          err instanceof ApiError
            ? err.message
            : err instanceof Error
              ? err.message
              : "Failed to load chat history.";
        setHistoryError(message);
      })
      .finally(() => {
        if (!cancelled) setLoadingHistory(false);
      });
    return () => {
      cancelled = true;
    };
  }, [initialChatId]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

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

  async function send() {
    const text = draft.trim();
    if (!text || streaming) return;

    setStreaming(true);
    setDraft("");

    // No chat_id => this is a new chat. The backend has no POST /chats route;
    // it creates the Chat row implicitly inside POST /chat/stream. We recover
    // the new id from GET /chats after the stream completes.
    const chatId = chatIdRef.current;
    const createdNewChat = !chatId;
    let receivedChatId = false;

    // The backend announces the new chat's id as the stream's first frame.
    // Apply it immediately so the URL deep-links before any content arrives.
    const applyChatId = (id: string) => {
      receivedChatId = true;
      if (chatIdRef.current === id) return;
      chatIdRef.current = id;
      // Soft URL update — keeps this component mounted (no router push).
      window.history.replaceState(null, "", `/chat/${id}`);
      window.dispatchEvent(new Event("chats:changed"));
    };

    const now = Date.now();
    const userMessage: ChatMessage = {
      id: `u-${now}`,
      role: "user",
      content: text,
      createdAt: new Date(now).toISOString(),
    };
    const assistantId = `a-${now + 1}`;
    const assistantMessage: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      createdAt: new Date(now + 1).toISOString(),
    };
    setMessages((prev) => [...prev, userMessage, assistantMessage]);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamChat(
        { message: text, chat_id: chatId },
        {
          signal: controller.signal,
          onChatId: applyChatId,
          onChunk: (chunk) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + chunk }
                  : m,
              ),
            );
          },
        },
      );
      if (createdNewChat && !receivedChatId) {
        // Fallback for backends that don't emit a chat_id frame: the stream
        // created the chat server-side, so recover its id from GET /chats
        // (ordered updated_at desc, so the just-created one is first).
        try {
          const [created] = await getChats();
          if (created) {
            chatIdRef.current = created.id;
            // Soft URL update — keeps this component mounted (no router push).
            window.history.replaceState(null, "", `/chat/${created.id}`);
          }
        } catch {
          // Non-fatal: the chat exists; the sidebar refresh below still reveals it.
        }
        window.dispatchEvent(new Event("chats:changed"));
      }
    } catch (err) {
      if ((err as Error)?.name === "AbortError") return;
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Something went wrong.";
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: m.content || `⚠ ${message}` }
            : m,
        ),
      );
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
      }
      setStreaming(false);
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="relative flex min-h-0 flex-1">
        <div
          ref={scrollRef}
          className="absolute inset-0 overflow-y-auto"
          aria-live="polite"
        >
          <div className="mx-auto w-full max-w-4xl px-3 py-6 sm:px-4">
            <div className="mb-6 border-b border-[var(--border)] pb-4">
              <h2 className="text-base font-semibold">{title}</h2>
              {subtitle && (
                <p className="mt-1 text-sm text-[var(--muted-foreground)]">
                  {subtitle}
                </p>
              )}
            </div>

            {loadingHistory ? (
              <HistorySkeleton />
            ) : historyError ? (
              <HistoryError message={historyError} />
            ) : messages.length === 0 ? (
              <EmptyState />
            ) : (
              <ul className="space-y-5">
                {messages.map((message) => (
                  <li key={message.id} data-message-id={message.id}>
                    <MessageBubble
                      message={message}
                      flash={flashId === message.id}
                      streaming={
                        streaming &&
                        message.role === "assistant" &&
                        message.content === ""
                      }
                    />
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <Checkpointer
          messages={messages}
          onJump={jumpTo}
          className="absolute right-3 top-1/2 z-10 -translate-y-1/2"
        />
      </div>

      <div className="border-t border-[var(--border)] bg-[var(--background)]">
        <Chatbox
          value={draft}
          onChange={setDraft}
          onSubmit={send}
          disabled={streaming || loadingHistory}
        />
      </div>
    </div>
  );
}

function MessageBubble({
  message,
  flash,
  streaming,
}: {
  message: ChatMessage;
  flash: boolean;
  streaming: boolean;
}) {
  const isUser = message.role === "user";
  return (
    <div
      className={cn(
        "flex items-start gap-3 transition-shadow",
        isUser && "flex-row-reverse",
        flash && "rounded-2xl ring-2 ring-[var(--ring)]/60",
      )}
    >
      <div
        className={cn(
          "inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser
            ? "bg-[var(--primary)] text-[var(--primary-foreground)]"
            : "bg-[var(--accent)] text-[var(--accent-foreground)]",
        )}
        aria-hidden
      >
        {isUser ? (
          <UserIcon className="h-4 w-4" />
        ) : (
          <MessageIcon className="h-4 w-4" />
        )}
      </div>
      <div
        className={cn(
          "max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
          isUser
            ? "bg-[var(--primary)] text-[var(--primary-foreground)]"
            : "bg-[var(--muted)] text-[var(--foreground)]",
        )}
      >
        {streaming ? (
          <TypingDots />
        ) : isUser ? (
          <span className="whitespace-pre-wrap">{message.content}</span>
        ) : (
          <MessageContent content={message.content} />
        )}
      </div>
    </div>
  );
}

function TypingDots() {
  return (
    <span className="inline-flex items-center gap-1 py-1" aria-label="Assistant is typing">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--muted-foreground)] [animation-delay:-0.3s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--muted-foreground)] [animation-delay:-0.15s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--muted-foreground)]" />
    </span>
  );
}

function HistorySkeleton() {
  return (
    <ul className="space-y-5" aria-busy="true" aria-label="Loading chat history">
      {[0, 1, 2].map((i) => (
        <li key={i} className={cn("flex items-start gap-3", i % 2 === 0 && "flex-row-reverse")}>
          <div className="h-8 w-8 shrink-0 animate-pulse rounded-full bg-[var(--muted)]" />
          <div className="h-12 w-2/3 animate-pulse rounded-2xl bg-[var(--muted)]" />
        </li>
      ))}
    </ul>
  );
}

function HistoryError({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="rounded-md border border-[var(--border)] bg-[var(--muted)] px-3 py-2 text-sm text-[var(--foreground)]"
    >
      Couldn&apos;t load chat history: {message}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--accent)] text-[var(--accent-foreground)]">
        <MessageIcon className="h-6 w-6" />
      </div>
      <h3 className="text-base font-semibold">Start a new conversation</h3>
      <p className="mt-1 max-w-sm text-sm text-[var(--muted-foreground)]">
        Ask a question, paste content, or describe what you&apos;d like help with.
      </p>
    </div>
  );
}
