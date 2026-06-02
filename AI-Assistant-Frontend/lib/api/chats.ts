import { apiFetch, parseError } from "./client";

export type ChatListItem = {
  id: string;
  title: string;
  updated_at: string;
};

export type MessageItem = {
  role: string;
  content: string;
  created_at: string;
};

export async function getChats(): Promise<ChatListItem[]> {
  const res = await apiFetch("/api/chats");
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as ChatListItem[];
}

export async function getMessages(chatId: string): Promise<MessageItem[]> {
  const res = await apiFetch(
    `/api/chats/${encodeURIComponent(chatId)}/messages`,
  );
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as MessageItem[];
}

// Delete a chat and everything it owns — messages, attachment records, the
// uploaded S3 files, the chat's Pinecone namespace, and its checkpointer thread
// (all server-side). The sidebar refreshes via the chats:changed event after.
export async function deleteChat(chatId: string): Promise<void> {
  const res = await apiFetch(`/api/chats/${encodeURIComponent(chatId)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw await parseError(res);
}
