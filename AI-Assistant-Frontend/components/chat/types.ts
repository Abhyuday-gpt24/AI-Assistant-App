export type MessageAttachment = {
  name: string;
  storagePath: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  attachments?: MessageAttachment[];
};
