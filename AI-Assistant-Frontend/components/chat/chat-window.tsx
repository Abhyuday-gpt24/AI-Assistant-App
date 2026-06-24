"use client";

import { Chatbox } from "./chatbox";
import { Checkpointer } from "./checkpointer";
import { MessageBubble } from "./message-bubble";
import { EmptyState, HistoryError, HistorySkeleton } from "./chat-states";
import { useState } from "react";
import { useChatId } from "./hooks/use-chat-id";
import { useChatHistory } from "./hooks/use-chat-history";
import { useChatScroll } from "./hooks/use-chat-scroll";
import { useChatStream } from "./hooks/use-chat-stream";
import { useUploads } from "./hooks/use-uploads";

type ChatWindowProps = {
  chatId?: string;
};

export function ChatWindow({
  chatId: initialChatId,
}: ChatWindowProps) {
  const [draft, setDraft] = useState("");

  const { chatIdRef, persistedRef } = useChatId(initialChatId);
  const { messages, setMessages, loadingHistory, historyError } =
    useChatHistory(initialChatId);
  const { scrollRef, flashId, jumpTo } = useChatScroll(messages);
  const { streaming, send } = useChatStream({
    chatIdRef,
    persistedRef,
    setMessages,
  });
  const uploads = useUploads(chatIdRef);

  async function handleSend() {
    const text = draft.trim();
    const { attachments, bubbleAttachments } = uploads.getReady();

    if ((!text && attachments.length === 0) || streaming) return;
    // Don't send while an upload is still in flight (no storage_path yet).
    if (uploads.hasUploading) return;

    setDraft("");
    uploads.reset();
    await send({ text, attachments, bubbleAttachments });
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
          onSubmit={handleSend}
          disabled={streaming || loadingHistory}
          attachments={uploads.attachedFiles}
          onAddFiles={uploads.addFiles}
          onRemoveAttachment={uploads.removeAttachment}
        />
      </div>
    </div>
  );
}
