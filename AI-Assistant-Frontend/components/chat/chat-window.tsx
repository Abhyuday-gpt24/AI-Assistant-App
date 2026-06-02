"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Chatbox, type AttachedFile } from "./chatbox";
import { Checkpointer } from "./checkpointer";
import { FileIcon, MessageIcon, UserIcon } from "@/components/ui/icons";
import { MessageContent } from "./message-content";
import { cn } from "@/lib/cn";
import type { ChatMessage, MessageAttachment } from "./types";
import { ApiError } from "@/lib/api/client";
import { streamChat } from "@/lib/api/chat";
import { getMessages, type MessageItem } from "@/lib/api/chats";
import {
  ALLOWED_UPLOAD_TYPES,
  MAX_FILES_PER_MESSAGE,
  uploadFile,
  triggerIngestion,
  getIngestionStatus,
  type Attachment,
} from "@/lib/api/uploads";

// Internal, richer shape than the Chatbox's display-only AttachedFile: it keeps
// the File and the storage_path we get back from S3 so send() can reuse it.
// ingestStatus tracks the RAG indexing of a *document* after it's uploaded.
type Upload = {
  id: string;
  name: string;
  file: File;
  status: "uploading" | "uploaded" | "error";
  storagePath?: string;
  category?: "images" | "docs";
  ingestStatus?: "indexing" | "ready" | "error";
  error?: string;
};

const ALLOWED_SET = new Set<string>(ALLOWED_UPLOAD_TYPES);

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
  const [uploads, setUploads] = useState<Upload[]>([]);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  // The chat_id is known up-front, even for a brand-new chat: we generate it
  // client-side so document ingestion can be scoped to THIS chat's RAG namespace
  // before the first message is ever sent. The backend creates the Chat row with
  // this same id on first send (and rejects it if it already belongs to someone
  // else). `persistedRef` tracks whether that server-side row exists yet.
  const chatIdRef = useRef<string | undefined>(initialChatId);
  // Lazy init ONLY — React permits writing a ref during render solely when it's
  // guarded by an `== null` check (one-time initialization). Generates a
  // client-side id for a brand-new chat so ingestion can be namespaced to it.
  if (chatIdRef.current == null) {
    chatIdRef.current = crypto.randomUUID();
  }
  const persistedRef = useRef<boolean>(Boolean(initialChatId));
  const abortRef = useRef<AbortController | null>(null);

  // When the chatId prop changes (navigating between chats can reuse this
  // component instance), reset the per-chat view state DURING render — React's
  // recommended alternative to syncing props in an effect. This also avoids the
  // "setState synchronously within an effect" cascading-render anti-pattern that
  // the history loader below would otherwise hit.
  const [trackedChatId, setTrackedChatId] = useState(initialChatId);
  if (trackedChatId !== initialChatId) {
    setTrackedChatId(initialChatId);
    setMessages([]);
    setHistoryError(null);
    setLoadingHistory(Boolean(initialChatId));
  }

  useEffect(() => {
    if (!initialChatId) return;
    let cancelled = false;
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

  // Step 2: a file was just attached. Validate it, show it as "uploading", then
  // presign + PUT it straight to S3 and stash the returned storage_path so Send
  // can reuse it without re-uploading.
  const addFiles = useCallback(
    (files: File[]) => {
      // Build the new entries first. Validation/count is done here (not inside
      // the setUploads updater) because React 19 StrictMode invokes state
      // updaters twice in dev — a presign+upload inside one would fire twice.
      const entries: Upload[] = [];
      let count = uploads.length;
      for (const file of files) {
        const id = crypto.randomUUID();
        if (!ALLOWED_SET.has(file.type)) {
          entries.push({
            id,
            name: file.name,
            file,
            status: "error",
            error: `Unsupported file type: ${file.type || "unknown"}`,
          });
          continue;
        }
        if (count >= MAX_FILES_PER_MESSAGE) {
          entries.push({
            id,
            name: file.name,
            file,
            status: "error",
            error: `Max ${MAX_FILES_PER_MESSAGE} files per message`,
          });
          continue;
        }
        count++;
        entries.push({ id, name: file.name, file, status: "uploading" });
      }

      setUploads((prev) => [...prev, ...entries]);

      // Fire the uploads OUTSIDE the updater so they run exactly once. The
      // reconciling setUploads calls below are pure (idempotent maps), so a
      // StrictMode double-invoke of them is harmless.
      for (const entry of entries) {
        if (entry.status !== "uploading") continue;
        uploadFile(entry.file)
          .then((uploaded) => {
            const isDoc = uploaded.category === "docs";
            setUploads((cur) =>
              cur.map((u) =>
                u.id === entry.id
                  ? {
                      ...u,
                      status: "uploaded",
                      storagePath: uploaded.storagePath,
                      category: uploaded.category,
                      // Docs begin indexing immediately; the poll effect below
                      // flips this to "ready"/"error".
                      ingestStatus: isDoc ? "indexing" : undefined,
                    }
                  : u,
              ),
            );
            // Step 5 trigger: documents get converted + embedded into THIS
            // chat's RAG namespace (chatIdRef is always set) now that they're in
            // S3. Images are skipped (sent to the model inline at send time).
            if (isDoc) {
              triggerIngestion(chatIdRef.current as string, [
                {
                  storage_path: uploaded.storagePath,
                  original_name: entry.name,
                  content_type: uploaded.contentType,
                },
              ]).catch(() => {
                // Couldn't even enqueue → mark errored so the chip isn't stuck.
                setUploads((cur) =>
                  cur.map((u) =>
                    u.id === entry.id ? { ...u, ingestStatus: "error" } : u,
                  ),
                );
              });
            }
          })
          .catch((err: unknown) => {
            const message =
              err instanceof Error ? err.message : "Upload failed";
            setUploads((cur) =>
              cur.map((u) =>
                u.id === entry.id ? { ...u, status: "error", error: message } : u,
              ),
            );
          });
      }
    },
    [uploads],
  );

  const removeAttachment = useCallback((id: string) => {
    setUploads((prev) => prev.filter((u) => u.id !== id));
  }, []);

  // Poll ingestion status while any document is still "indexing". The key is a
  // stable join of the indexing paths, so the loop restarts when that set
  // changes (a doc turning ready/error drops out and the loop shrinks).
  const indexingKey = uploads
    .filter((u) => u.ingestStatus === "indexing" && u.storagePath)
    .map((u) => u.storagePath as string)
    .sort()
    .join("|");

  useEffect(() => {
    if (!indexingKey) return;
    const paths = indexingKey.split("|");
    let cancelled = false;
    let timer: number | undefined;

    const tick = async () => {
      try {
        const statuses = await getIngestionStatus(paths);
        if (cancelled) return;
        setUploads((cur) =>
          cur.map((u) => {
            if (u.ingestStatus !== "indexing" || !u.storagePath) return u;
            const s = statuses.find((x) => x.storage_path === u.storagePath);
            if (!s) return u;
            if (s.status === "ready") return { ...u, ingestStatus: "ready" };
            if (s.status === "error")
              return { ...u, ingestStatus: "error", error: s.error ?? "Indexing failed" };
            return u; // pending/processing → keep polling
          }),
        );
      } catch {
        // transient network/error — keep polling
      }
      if (!cancelled) timer = window.setTimeout(tick, 2500);
    };

    timer = window.setTimeout(tick, 1500);
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [indexingKey]);

  // Display-only projection handed to the Chatbox.
  const attachedFiles: AttachedFile[] = uploads.map((u) => ({
    id: u.id,
    name: u.name,
    status: u.status,
    ingestStatus: u.ingestStatus,
    error: u.error,
  }));

  async function send() {
    const text = draft.trim();

    // Only files that finished uploading carry a storage_path we can send.
    const ready = uploads.filter(
      (u) => u.status === "uploaded" && u.storagePath,
    );
    const attachments: Attachment[] = ready.map((u) => ({
      original_name: u.name,
      storage_path: u.storagePath as string,
    }));
    const bubbleAttachments: MessageAttachment[] = ready.map((u) => ({
      name: u.name,
      storagePath: u.storagePath as string,
    }));

    if ((!text && attachments.length === 0) || streaming) return;
    // Don't send while an upload is still in flight (no storage_path yet).
    if (uploads.some((u) => u.status === "uploading")) return;

    setStreaming(true);
    setDraft("");
    setUploads([]);

    // The chat_id is always known (client-generated for new chats). The backend
    // creates the Chat row with this id on first send; `persistedRef` tells us
    // whether that's happened yet, so we know to deep-link the URL + refresh the
    // sidebar the first time.
    const chatId = chatIdRef.current as string;
    const createdNewChat = !persistedRef.current;
    let receivedChatId = false;

    // The backend echoes the chat id as the stream's first frame. For a new chat
    // this is our own generated id; apply it once to deep-link the URL and reveal
    // the chat in the sidebar.
    const applyChatId = (id: string) => {
      receivedChatId = true;
      chatIdRef.current = id;
      const firstPersist = !persistedRef.current;
      persistedRef.current = true;
      if (firstPersist) {
        // Soft URL update — keeps this component mounted (no router push).
        window.history.replaceState(null, "", `/chat/${id}`);
        window.dispatchEvent(new Event("chats:changed"));
      }
    };

    const now = Date.now();
    const userMessage: ChatMessage = {
      id: `u-${now}`,
      role: "user",
      content: text,
      createdAt: new Date(now).toISOString(),
      attachments: bubbleAttachments.length > 0 ? bubbleAttachments : undefined,
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
        {
          message: text,
          chat_id: chatId,
          attachments: attachments.length > 0 ? attachments : undefined,
        },
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
        // Fallback for backends that don't emit a chat_id frame: we already hold
        // the client-generated id the backend created the chat under, so just
        // deep-link the URL and refresh the sidebar.
        persistedRef.current = true;
        // Soft URL update — keeps this component mounted (no router push).
        window.history.replaceState(null, "", `/chat/${chatId}`);
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
            <div className="mb-6 border-b border-border pb-4">
              <h2 className="text-base font-semibold">{title}</h2>
              {subtitle && (
                <p className="mt-1 text-sm text-muted-foreground">
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

      <div className="border-t border-border bg-background">
        <Chatbox
          value={draft}
          onChange={setDraft}
          onSubmit={send}
          disabled={streaming || loadingHistory}
          attachments={attachedFiles}
          onAddFiles={addFiles}
          onRemoveAttachment={removeAttachment}
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
        flash && "rounded-2xl ring-2 ring-(--ring)/60",
      )}
    >
      <div
        className={cn(
          "inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-accent text-accent-foreground",
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
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-foreground",
        )}
      >
        {streaming ? (
          <TypingDots />
        ) : isUser ? (
          <div className="space-y-2">
            {message.attachments && message.attachments.length > 0 && (
              <ul className="flex flex-wrap gap-1.5">
                {message.attachments.map((att) => (
                  <li
                    key={att.storagePath}
                    className="flex max-w-50 items-center gap-1.5 rounded-lg bg-(--primary-foreground)/15 px-2 py-1 text-xs"
                  >
                    <FileIcon className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate" title={att.name}>
                      {att.name}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            {message.content && (
              <span className="block whitespace-pre-wrap">{message.content}</span>
            )}
          </div>
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
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground" />
    </span>
  );
}

function HistorySkeleton() {
  return (
    <ul className="space-y-5" aria-busy="true" aria-label="Loading chat history">
      {[0, 1, 2].map((i) => (
        <li key={i} className={cn("flex items-start gap-3", i % 2 === 0 && "flex-row-reverse")}>
          <div className="h-8 w-8 shrink-0 animate-pulse rounded-full bg-muted" />
          <div className="h-12 w-2/3 animate-pulse rounded-2xl bg-muted" />
        </li>
      ))}
    </ul>
  );
}

function HistoryError({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="rounded-md border border-border bg-muted px-3 py-2 text-sm text-foreground"
    >
      Couldn&apos;t load chat history: {message}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-accent text-accent-foreground">
        <MessageIcon className="h-6 w-6" />
      </div>
      <h3 className="text-base font-semibold">Start a new conversation</h3>
      <p className="mt-1 max-w-sm text-sm text-muted-foreground">
        Ask a question, paste content, or describe what you&apos;d like help with.
      </p>
    </div>
  );
}
