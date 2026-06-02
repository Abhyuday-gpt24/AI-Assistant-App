// Cross-component browser event: the chat stream dispatches this after a new
// chat is first persisted so the sidebar can refresh its list. Kept here (not in
// the sidebar) so producer and consumer share one source of truth.
export const CHATS_CHANGED_EVENT = "chats:changed";

export function emitChatsChanged() {
  window.dispatchEvent(new Event(CHATS_CHANGED_EVENT));
}
