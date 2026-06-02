"use client";

import Link from "next/link";
import { cn } from "@/lib/cn";
import { MessageIcon, TrashIcon, SpinnerIcon } from "@/components/ui/icons";
import type { ChatListItem } from "@/lib/api/chats";

export function ChatList({
  collapsed,
  query,
  activePath,
  onCloseMobile,
  filteredChats,
  loadingChats,
  chatsError,
  onDeleteChat,
  deletingId,
}: {
  collapsed: boolean;
  query: string;
  activePath: string;
  onCloseMobile: () => void;
  filteredChats: ChatListItem[];
  loadingChats: boolean;
  chatsError: string | null;
  onDeleteChat: (id: string, title: string) => void;
  deletingId: string | null;
}) {
  return (
    <nav className="flex-1 overflow-y-auto px-2 pb-3">
      {/* Hidden when collapsed (icon-only chat rows aren't useful); the nav
          stays as the flex spacer so the footer remains pinned to the bottom. */}
      <div className={cn(collapsed && "md:hidden")}>
        <p
          className={cn(
            "px-2 py-2 text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]",
            collapsed && "md:hidden",
          )}
        >
          Recent
        </p>

        {loadingChats ? (
          <ChatListSkeleton collapsed={collapsed} />
        ) : chatsError ? (
          <ChatListError message={chatsError} collapsed={collapsed} />
        ) : (
          <ul className="space-y-1">
            {filteredChats.map((chat) => (
              <ChatRow
                key={chat.id}
                chat={chat}
                isActive={activePath === `/chat/${chat.id}`}
                collapsed={collapsed}
                onCloseMobile={onCloseMobile}
                onDeleteChat={onDeleteChat}
                deleting={deletingId === chat.id}
              />
            ))}
            {filteredChats.length === 0 && (
              <li
                className={cn(
                  "px-2 py-4 text-sm text-[var(--muted-foreground)]",
                  collapsed && "md:hidden",
                )}
              >
                {query ? "No chats found." : "No chats yet."}
              </li>
            )}
          </ul>
        )}
      </div>
    </nav>
  );
}

function ChatRow({
  chat,
  isActive,
  collapsed,
  onCloseMobile,
  onDeleteChat,
  deleting,
}: {
  chat: ChatListItem;
  isActive: boolean;
  collapsed: boolean;
  onCloseMobile: () => void;
  onDeleteChat: (id: string, title: string) => void;
  deleting: boolean;
}) {
  const href = `/chat/${chat.id}`;

  return (
    <li className="group relative">
      <Link
        href={href}
        onClick={onCloseMobile}
        title={chat.title}
        className={cn(
          "flex items-center gap-2 rounded-md px-2 py-2 pr-9 text-sm transition-colors",
          isActive
            ? "bg-[var(--accent)] text-[var(--accent-foreground)]"
            : "text-[var(--foreground)] hover:bg-[var(--accent)]",
          collapsed && "md:justify-center md:px-0",
        )}
      >
        <MessageIcon className="h-4 w-4 shrink-0" />
        <span className={cn("truncate", collapsed && "md:hidden")}>
          {chat.title}
        </span>
      </Link>

      {/* The delete button is a SIBLING of the Link (not nested — a button inside
          an anchor is invalid), absolutely positioned over the row's right edge
          so a click deletes without navigating into the chat. Confirmation and
          the actual delete live in the Sidebar handler (owns routing + dialog). */}
      <button
        type="button"
        onClick={() => onDeleteChat(chat.id, chat.title)}
        disabled={deleting}
        title="Delete chat"
        aria-label={`Delete chat ${chat.title}`}
        className={cn(
          "absolute right-1 top-1/2 grid h-7 w-7 -translate-y-1/2 place-items-center rounded-md text-[var(--muted-foreground)] transition-opacity hover:bg-[var(--background)] hover:text-red-500 focus:outline-none focus:ring-2 focus:ring-[var(--ring)]/40 disabled:opacity-100",
          // Hidden until row hover / keyboard focus; always shown while deleting.
          deleting
            ? "opacity-100"
            : "opacity-0 focus-visible:opacity-100 group-hover:opacity-100",
          collapsed && "md:hidden",
        )}
      >
        {deleting ? (
          <SpinnerIcon className="h-4 w-4 animate-spin" />
        ) : (
          <TrashIcon className="h-4 w-4" />
        )}
      </button>
    </li>
  );
}

function ChatListSkeleton({ collapsed }: { collapsed: boolean }) {
  return (
    <ul className="space-y-1" aria-busy="true" aria-label="Loading chats">
      {[0, 1, 2, 3].map((i) => (
        <li
          key={i}
          className={cn(
            "flex items-center gap-2 px-2 py-2",
            collapsed && "md:justify-center md:px-0",
          )}
        >
          <div className="h-4 w-4 shrink-0 animate-pulse rounded bg-[var(--muted)]" />
          <div
            className={cn(
              "h-3 w-full animate-pulse rounded bg-[var(--muted)]",
              collapsed && "md:hidden",
            )}
          />
        </li>
      ))}
    </ul>
  );
}

function ChatListError({
  message,
  collapsed,
}: {
  message: string;
  collapsed: boolean;
}) {
  return (
    <p
      role="alert"
      className={cn(
        "px-2 py-3 text-sm text-[var(--muted-foreground)]",
        collapsed && "md:hidden",
      )}
    >
      {message}
    </p>
  );
}
