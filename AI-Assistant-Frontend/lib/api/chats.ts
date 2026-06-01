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
