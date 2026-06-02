import { useCallback, useEffect, useMemo, useState } from "react";
import { getChats, type ChatListItem } from "@/lib/api/chats";
import { errorMessage } from "@/lib/api/error-message";
import { CHATS_CHANGED_EVENT } from "@/lib/events";

export type ChatsState = {
  chats: ChatListItem[];
  filteredChats: ChatListItem[];
  loadingChats: boolean;
  chatsError: string | null;
};

// Owns the sidebar's chat list: loads it, refreshes on the chats:changed event
// (fired after a new chat is first persisted), and applies the search filter.
export function useChats(query: string): ChatsState {
  const [chats, setChats] = useState<ChatListItem[]>([]);
  const [loadingChats, setLoadingChats] = useState(true);
  const [chatsError, setChatsError] = useState<string | null>(null);

  const refreshChats = useCallback(() => {
    let cancelled = false;
    setLoadingChats(true);
    setChatsError(null);
    getChats()
      .then((items) => {
        if (!cancelled) setChats(items);
      })
      .catch((err) => {
        if (cancelled) return;
        setChatsError(errorMessage(err, "Failed to load chats."));
      })
      .finally(() => {
        if (!cancelled) setLoadingChats(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const cleanup = refreshChats();
    return cleanup;
  }, [refreshChats]);

  useEffect(() => {
    const handler = () => {
      refreshChats();
    };
    window.addEventListener(CHATS_CHANGED_EVENT, handler);
    return () => window.removeEventListener(CHATS_CHANGED_EVENT, handler);
  }, [refreshChats]);

  const filteredChats = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return chats;
    return chats.filter((c) => c.title.toLowerCase().includes(q));
  }, [query, chats]);

  return { chats, filteredChats, loadingChats, chatsError };
}
