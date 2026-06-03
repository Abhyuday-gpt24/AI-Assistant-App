import { apiFetch, parseError } from "./client";
import type { Attachment } from "./uploads";

export type StreamChatBody = {
  message: string;
  // Omitted for a brand-new chat — the backend creates the Chat row inside
  // POST /chat/stream when chat_id is absent. There is no POST /chats route.
  chat_id?: string;
  // Set when this is a chat inside a project: on first send the backend creates
  // the chat under the project so its RAG namespace is the project's shared
  // corpus. Ignored for an already-persisted chat (the stored value wins).
  project_id?: string;
  // Files already uploaded to S3 (presigned flow). The backend re-verifies
  // each one exists before streaming. Omitted/empty when nothing is attached.
  attachments?: Attachment[];
};

export type StreamChatOptions = {
  onChunk: (chunk: string) => void;
  // Fired when the backend announces the (possibly newly created) chat id as
  // the first frame of the stream — lets the caller deep-link before content.
  onChatId?: (chatId: string) => void;
  onDone?: () => void;
  signal?: AbortSignal;
};

// The backend stream emits these JSON frame shapes over the SSE stream:
//   {"chat_id": "..."} — id of the (possibly new) chat, sent as the first frame
//   {"delta": "..."}   — an incremental slice of the assistant's reply
//   {"error": "..."}   — the stream failed server-side (terminal)
// plus a bare "[DONE]" sentinel (handled by the caller). Parse a content frame
// into its delta text, surface a chat id, or signal an error to be thrown.
function parseFrame(
  payload: string,
): { text: string; chatId?: string; error?: string } {
  try {
    const parsed = JSON.parse(payload) as {
      delta?: unknown;
      chat_id?: unknown;
      error?: unknown;
    };
    if (typeof parsed.error === "string") return { text: "", error: parsed.error };
    if (typeof parsed.chat_id === "string")
      return { text: "", chatId: parsed.chat_id };
    if (typeof parsed.delta === "string") return { text: parsed.delta };
  } catch {
    // not JSON — treat the raw payload as text (defensive fallback)
  }
  return { text: payload };
}

export async function streamChat(
  body: StreamChatBody,
  { onChunk, onChatId, onDone, signal }: StreamChatOptions,
): Promise<void> {
  const res = await apiFetch("/api/chat/stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) throw await parseError(res);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const flushFrames = () => {
    let idx = buffer.indexOf("\n\n");
    while (idx !== -1) {
      const frame = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const dataLines = frame
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).replace(/^ /, ""));
      if (dataLines.length > 0) {
        const payload = dataLines.join("\n");
        if (payload === "[DONE]") {
          onDone?.();
          return true;
        }
        const frame = parseFrame(payload);
        if (frame.error) throw new Error(frame.error);
        if (frame.chatId !== undefined) {
          onChatId?.(frame.chatId);
        } else {
          onChunk(frame.text);
        }
      }
      idx = buffer.indexOf("\n\n");
    }
    return false;
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      if (flushFrames()) return;
    }
    buffer += decoder.decode();
    if (!flushFrames()) onDone?.();
  } finally {
    reader.releaseLock();
  }
}
