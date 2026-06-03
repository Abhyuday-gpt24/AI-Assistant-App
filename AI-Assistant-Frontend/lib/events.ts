// Cross-component browser event: the chat stream dispatches this after a new
// chat is first persisted so the sidebar can refresh its list. Kept here (not in
// the sidebar) so producer and consumer share one source of truth.
export const CHATS_CHANGED_EVENT = "chats:changed";

export function emitChatsChanged() {
  window.dispatchEvent(new Event(CHATS_CHANGED_EVENT));
}

// Clicking "New chat" emits this so the index chat page can force a fresh
// ChatWindow (remount). It can't rely on route navigation alone: a brand-new
// chat's first send deep-links the URL to `/chat/{id}` via
// `window.history.replaceState` WITHOUT a router navigation, so the app stays on
// the `/chat` index segment. Navigating index→index then reuses the same
// ChatWindow instance (identical props) and nothing resets. This explicit signal
// — fired only on a real New-chat click, never on the streaming replaceState —
// bumps a remount key so the window truly starts over.
export const NEW_CHAT_EVENT = "chat:new";

export function emitNewChat() {
  window.dispatchEvent(new Event(NEW_CHAT_EVENT));
}

// Fired after a project is created, renamed, or deleted so the sidebar's
// ProjectsSection (and the /projects grid) can refresh their lists. Same
// publish/subscribe shape as chats:changed, kept here as the shared contract.
export const PROJECTS_CHANGED_EVENT = "projects:changed";

export function emitProjectsChanged() {
  window.dispatchEvent(new Event(PROJECTS_CHANGED_EVENT));
}
