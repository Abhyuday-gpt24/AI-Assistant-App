import { useCallback, useEffect, useMemo, useState } from "react";
import { getChats, type ChatListItem } from "@/lib/api/chats";
import { errorMessage } from "@/lib/api/error-message";
import { CHATS_CHANGED_EVENT } from "@/lib/events";

export type ChatsState = {
  chats: ChatListItem[];
  filteredChats: ChatListItem[];
  loadingChats: boolean;
  chatsError: string | null;
  /**
   * Remove a chat from the list IMMEDIATELY (optimistic delete) and return a
   * rollback that restores the prior list — call it if the server delete fails.
   */
  removeChatOptimistic: (id: string) => () => void;
};

// Owns the sidebar's chat list: loads it, refreshes on the chats:changed event
// (fired after a chat is created/deleted), and applies the search filter.
//
// State is reconciled ONLY in async callbacks — never synchronously in an effect
// — so (a) it doesn't trip the set-state-in-effect lint rule and (b) a background
// refresh doesn't flip `loadingChats` true, which previously blanked the whole
// list to a skeleton on every change (the "delete makes Recents flash" bug).
// `loadingChats` is therefore true only for the very first load.
export function useChats(query: string): ChatsState {
  const [chats, setChats] = useState<ChatListItem[]>([]);
  const [loadingChats, setLoadingChats] = useState(true);
  const [chatsError, setChatsError] = useState<string | null>(null);

  const load = useCallback((flag: { cancelled: boolean }) => {
    getChats()
      .then((items) => {
        if (flag.cancelled) return;
        setChats(items);
        setChatsError(null);
      })
      .catch((err) => {
        if (!flag.cancelled) setChatsError(errorMessage(err, "Failed to load chats."));
      })
      .finally(() => {
        if (!flag.cancelled) setLoadingChats(false);
      });
  }, []);

  useEffect(() => {
    const flag = { cancelled: false };
    load(flag);
    return () => {
      flag.cancelled = true;
    };
  }, [load]);

  useEffect(() => {
    const handler = () => load({ cancelled: false });
    window.addEventListener(CHATS_CHANGED_EVENT, handler);
    return () => window.removeEventListener(CHATS_CHANGED_EVENT, handler);
  }, [load]);

  const removeChatOptimistic = useCallback((id: string) => {
    let snapshot: ChatListItem[] = [];
    setChats((prev) => {
      snapshot = prev; // capture for rollback (pure: same prev on a StrictMode re-invoke)
      return prev.filter((c) => c.id !== id);
    });
    return () => setChats(snapshot);
  }, []);

  const filteredChats = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return chats;
    return chats.filter((c) => c.title.toLowerCase().includes(q));
  }, [query, chats]);

  return { chats, filteredChats, loadingChats, chatsError, removeChatOptimistic };
}
