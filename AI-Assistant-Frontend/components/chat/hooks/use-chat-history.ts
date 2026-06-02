import { useEffect, useState, type Dispatch, type SetStateAction } from "react";
import { getMessages } from "@/lib/api/chats";
import { errorMessage } from "@/lib/api/error-message";
import type { ChatMessage } from "../types";
import { toChatMessage } from "../messages";

export type ChatHistory = {
  messages: ChatMessage[];
  setMessages: Dispatch<SetStateAction<ChatMessage[]>>;
  loadingHistory: boolean;
  historyError: string | null;
};

// Owns the message list for a chat: loads persisted history when a chatId is
// present and resets the per-chat view state when the prop changes (navigating
// between chats can reuse this component instance).
export function useChatHistory(initialChatId?: string): ChatHistory {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(
    Boolean(initialChatId),
  );
  const [historyError, setHistoryError] = useState<string | null>(null);

  // Reset per-chat view state DURING render — React's recommended alternative to
  // syncing props in an effect. This also avoids the "setState synchronously
  // within an effect" cascading-render anti-pattern the loader below would hit.
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
        setHistoryError(errorMessage(err, "Failed to load chat history."));
      })
      .finally(() => {
        if (!cancelled) setLoadingHistory(false);
      });
    return () => {
      cancelled = true;
    };
  }, [initialChatId]);

  return { messages, setMessages, loadingHistory, historyError };
}
