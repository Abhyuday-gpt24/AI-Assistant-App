"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useState } from "react";
import { cn } from "@/lib/cn";
import { deleteChat } from "@/lib/api/chats";
import { emitChatsChanged, emitNewChat } from "@/lib/events";
import { useDialog } from "@/components/ui/dialog";
import { PlusIcon, SearchIcon } from "@/components/ui/icons";
import { SidebarHeader } from "./sidebar/sidebar-header";
import { SidebarFooter } from "./sidebar/sidebar-footer";
import { ChatList } from "./sidebar/chat-list";
import { useChats } from "./sidebar/use-chats";

type SidebarProps = {
  collapsed: boolean;
  mobileOpen: boolean;
  onToggleCollapsed: () => void;
  onCloseMobile: () => void;
};

export function Sidebar({
  collapsed,
  mobileOpen,
  onToggleCollapsed,
  onCloseMobile,
}: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { confirm, alert } = useDialog();
  const [query, setQuery] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const { filteredChats, loadingChats, chatsError, removeChatOptimistic } =
    useChats(query);

  // Confirm, then delete the chat (and its server-side files/namespace) and
  // refresh the list. If the deleted chat is the one open, fall back to a fresh
  // New chat. Owns the per-row `deletingId` so the row only renders the spinner.
  const handleDeleteChat = useCallback(
    async (id: string, title: string) => {
      const ok = await confirm({
        title: "Delete chat",
        message: `Delete "${title}"? This also removes its uploaded files and can't be undone.`,
        confirmLabel: "Delete",
        cancelLabel: "Cancel",
        variant: "danger",
      });
      if (!ok) return;

      setDeletingId(id);
      // Optimistic: drop the row instantly so the list doesn't wait on the round
      // trip (and never flashes a skeleton). Restore it if the delete fails.
      const rollback = removeChatOptimistic(id);
      try {
        await deleteChat(id);
        // Re-sync the list — already removed locally, so this is a silent
        // background refresh, not a visible reload.
        emitChatsChanged();
        if (pathname === `/chat/${id}`) {
          router.push("/chat");
          emitNewChat();
        }
      } catch {
        rollback();
        await alert({
          title: "Delete failed",
          message: "Couldn't delete the chat. Please try again.",
        });
      } finally {
        setDeletingId(null);
      }
    },
    [confirm, alert, pathname, router, removeChatOptimistic],
  );

  return (
    <>
      <div
        className={cn(
          "fixed inset-0 z-30 bg-black/40 transition-opacity md:hidden",
          mobileOpen
            ? "pointer-events-auto opacity-100"
            : "pointer-events-none opacity-0",
        )}
        onClick={onCloseMobile}
        aria-hidden
      />

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex flex-col border-r border-[var(--border)] bg-[var(--card)] text-[var(--card-foreground)] transition-[width,transform] duration-200 ease-out",
          "md:static md:translate-x-0",
          collapsed ? "md:w-16" : "md:w-72",
          "w-72",
          mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
        )}
        aria-label="Chats sidebar"
      >
        <SidebarHeader
          collapsed={collapsed}
          onToggleCollapsed={onToggleCollapsed}
          onCloseMobile={onCloseMobile}
        />

        <div className="px-2 pt-3 pb-2">
          <Link
            href="/chat"
            onClick={() => {
              // Force a fresh chat even when the URL is already `/chat`
              // (after a prior chat's streaming replaceState left us on this
              // index segment, a plain index→index nav reuses the window).
              emitNewChat();
              onCloseMobile();
            }}
            title="New chat"
            className={cn(
              "flex w-full items-center gap-2 rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] px-3 py-2 text-sm font-medium hover:opacity-90",
              collapsed && "md:justify-center md:px-0",
            )}
          >
            <PlusIcon className="h-4 w-4 shrink-0" />
            <span className={cn(collapsed && "md:hidden")}>New chat</span>
          </Link>
        </div>

        <div className={cn("px-2 pt-3 pb-2", collapsed && "md:hidden")}>
          <label className="relative block">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted-foreground)]" />
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search chats"
              className="h-9 w-full rounded-md border border-[var(--input)] bg-[var(--background)] pl-9 pr-3 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]/40"
            />
          </label>
        </div>

        <ChatList
          collapsed={collapsed}
          query={query}
          activePath={pathname}
          onCloseMobile={onCloseMobile}
          filteredChats={filteredChats}
          loadingChats={loadingChats}
          chatsError={chatsError}
          onDeleteChat={handleDeleteChat}
          deletingId={deletingId}
        />

        <SidebarFooter collapsed={collapsed} />
      </aside>
    </>
  );
}
