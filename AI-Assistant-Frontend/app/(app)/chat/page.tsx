"use client";

import { useEffect, useState } from "react";
import { ChatWindow } from "@/components/chat/chat-window";
import { NEW_CHAT_EVENT } from "@/lib/events";

export default function ChatIndexPage() {
  // A brand-new chat's first send deep-links the URL to `/chat/{id}` with
  // `window.history.replaceState` (no router navigation, so the stream survives),
  // which leaves the app rendering THIS index segment. Clicking "New chat" then
  // navigates index→index and React would reuse the same ChatWindow instance —
  // so the old conversation never clears. Bumping this key on the New-chat signal
  // forces a fresh ChatWindow (full reset of messages/chatId/uploads). We listen
  // to the event rather than `usePathname` precisely so the streaming
  // replaceState (which DOES update the pathname) never triggers a remount.
  const [resetKey, setResetKey] = useState(0);

  useEffect(() => {
    const onNewChat = () => setResetKey((k) => k + 1);
    window.addEventListener(NEW_CHAT_EVENT, onNewChat);
    return () => window.removeEventListener(NEW_CHAT_EVENT, onNewChat);
  }, []);

  return <ChatWindow key={resetKey} />;
}
