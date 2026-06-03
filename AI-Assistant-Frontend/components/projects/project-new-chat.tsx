"use client";

import { useEffect, useState } from "react";
import { ChatWindow } from "@/components/chat/chat-window";
import { NEW_CHAT_EVENT } from "@/lib/events";

// A brand-new chat INSIDE a project. Same remount dance as the global chat index
// page: the first send deep-links the URL to /projects/{id}/chat/{chatId} via a
// soft history.replaceState (no router nav, so the stream survives), which leaves
// this segment rendered. A New-chat click then emits NEW_CHAT_EVENT and we bump
// the key to force a fresh ChatWindow (new client-generated chatId + cleared
// state). projectId stays fixed so uploads/stream keep targeting this project.
export function ProjectNewChat({ projectId }: { projectId: string }) {
  const [resetKey, setResetKey] = useState(0);

  useEffect(() => {
    const onNewChat = () => setResetKey((k) => k + 1);
    window.addEventListener(NEW_CHAT_EVENT, onNewChat);
    return () => window.removeEventListener(NEW_CHAT_EVENT, onNewChat);
  }, []);

  return (
    <ChatWindow
      key={resetKey}
      projectId={projectId}
      title="New chat"
      subtitle="Documents you attach here are shared across this project."
    />
  );
}
