import type { ChatMessage, MessageAttachment } from "./types";
import type { MessageItem } from "@/lib/api/chats";

// Map a persisted history row into the view's ChatMessage shape. The index keeps
// the synthetic id stable across a render of the same loaded history.
export function toChatMessage(m: MessageItem, index: number): ChatMessage {
  return {
    id: `h-${index}-${m.created_at}`,
    role: m.role === "user" ? "user" : "assistant",
    content: m.content,
    createdAt: m.created_at,
  };
}

// Build the user + (empty) assistant pair appended optimistically on send. The
// assistant bubble starts empty and is filled in as stream chunks arrive, keyed
// by the returned assistantId.
export function createMessagePair(
  text: string,
  attachments?: MessageAttachment[],
): { userMessage: ChatMessage; assistantMessage: ChatMessage; assistantId: string } {
  const now = Date.now();
  const userMessage: ChatMessage = {
    id: `u-${now}`,
    role: "user",
    content: text,
    createdAt: new Date(now).toISOString(),
    attachments: attachments && attachments.length > 0 ? attachments : undefined,
  };
  const assistantId = `a-${now + 1}`;
  const assistantMessage: ChatMessage = {
    id: assistantId,
    role: "assistant",
    content: "",
    createdAt: new Date(now + 1).toISOString(),
  };
  return { userMessage, assistantMessage, assistantId };
}
