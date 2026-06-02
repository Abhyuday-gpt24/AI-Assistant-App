import { useRef } from "react";
import { randomUUID } from "@/lib/uuid";

export type ChatIdState = {
  // The chat_id is known up-front, even for a brand-new chat: it's generated
  // client-side so document ingestion can be scoped to THIS chat's RAG namespace
  // before the first message is ever sent. The backend creates the Chat row with
  // this same id on first send (and rejects it if it already belongs to someone
  // else).
  chatIdRef: React.RefObject<string | undefined>;
  // Whether the server-side Chat row exists yet. Lets send() know to deep-link
  // the URL + refresh the sidebar the first time a new chat is persisted.
  persistedRef: React.RefObject<boolean>;
};

export function useChatId(initialChatId?: string): ChatIdState {
  const chatIdRef = useRef<string | undefined>(initialChatId);
  // Lazy init ONLY — React permits writing a ref during render solely when it's
  // guarded by an `== null` check (one-time initialization). Generates a
  // client-side id for a brand-new chat so ingestion can be namespaced to it.
  if (chatIdRef.current == null) {
    chatIdRef.current = randomUUID();
  }
  const persistedRef = useRef<boolean>(Boolean(initialChatId));

  return { chatIdRef, persistedRef };
}
