import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";
import { streamChat } from "@/lib/api/chat";
import { errorMessage } from "@/lib/api/error-message";
import { emitChatsChanged } from "@/lib/events";
import type { Attachment } from "@/lib/api/uploads";
import type { ChatMessage, MessageAttachment } from "../types";
import { createMessagePair } from "../messages";
import type { ChatIdState } from "./use-chat-id";

type SendArgs = {
  text: string;
  attachments: Attachment[];
  bubbleAttachments: MessageAttachment[];
};

type UseChatStreamArgs = ChatIdState & {
  setMessages: Dispatch<SetStateAction<ChatMessage[]>>;
};

export type ChatStream = {
  streaming: boolean;
  send: (args: SendArgs) => Promise<void>;
};

// Owns the send/stream lifecycle: appends the optimistic message pair, streams
// the assistant reply into it, and handles first-persist URL deep-linking +
// sidebar refresh for brand-new chats. Aborts any in-flight stream on unmount.
export function useChatStream({
  chatIdRef,
  persistedRef,
  setMessages,
}: UseChatStreamArgs): ChatStream {
  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const send = useCallback(
    async ({ text, attachments, bubbleAttachments }: SendArgs) => {
      // The chat_id is always known (client-generated for new chats). The backend
      // creates the Chat row with this id on first send; `persistedRef` tells us
      // whether that's happened yet, so we know to deep-link the URL + refresh
      // the sidebar the first time.
      const chatId = chatIdRef.current as string;
      const createdNewChat = !persistedRef.current;
      let receivedChatId = false;

      // Where a freshly-persisted chat's URL should point.
      const chatPath = (id: string) => `/chat/${id}`;

      // The backend echoes the chat id as the stream's first frame. For a new
      // chat this is our own generated id; apply it once to deep-link the URL and
      // reveal the chat in the sidebar.
      const applyChatId = (id: string) => {
        receivedChatId = true;
        chatIdRef.current = id;
        const firstPersist = !persistedRef.current;
        persistedRef.current = true;
        if (firstPersist) {
          // Soft URL update — keeps this component mounted (no router push).
          window.history.replaceState(null, "", chatPath(id));
          emitChatsChanged();
        }
      };

      const { userMessage, assistantMessage, assistantId } = createMessagePair(
        text,
        bubbleAttachments,
      );
      setMessages((prev) => [...prev, userMessage, assistantMessage]);

      const controller = new AbortController();
      abortRef.current = controller;
      setStreaming(true);

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
          // Fallback for backends that don't emit a chat_id frame: we already
          // hold the client-generated id the backend created the chat under, so
          // just deep-link the URL and refresh the sidebar.
          persistedRef.current = true;
          // Soft URL update — keeps this component mounted (no router push).
          window.history.replaceState(null, "", chatPath(chatId));
          emitChatsChanged();
        }
      } catch (err) {
        if ((err as Error)?.name === "AbortError") return;
        const message = errorMessage(err, "Something went wrong.");
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
    },
    [chatIdRef, persistedRef, setMessages],
  );

  return { streaming, send };
}
