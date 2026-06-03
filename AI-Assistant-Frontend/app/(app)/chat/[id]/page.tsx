import { ChatWindow } from "@/components/chat/chat-window";

export default async function ChatDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ChatWindow chatId={id} />;
}
