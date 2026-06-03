import { ChatWindow } from "@/components/chat/chat-window";

// An existing chat inside a project. Both ids come from the route; the window
// loads the chat's history and scopes uploads/stream to the project's shared
// corpus. (The backend also resolves the namespace from the stored chat, so this
// is correct even though the namespace lives server-side.)
export default async function ProjectChatPage({
  params,
}: {
  params: Promise<{ id: string; chatId: string }>;
}) {
  const { id, chatId } = await params;
  return <ChatWindow projectId={id} chatId={chatId} />;
}
