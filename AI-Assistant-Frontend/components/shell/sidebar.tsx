"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { cn } from "@/lib/cn";
import { DUMMY_PROJECTS } from "@/lib/projects";
import { ApiError } from "@/lib/api/client";
import { getChats, type ChatListItem } from "@/lib/api/chats";
import { useAuth } from "@/components/auth/auth-provider";
import {
  ChevronRightIcon,
  CloseIcon,
  FolderIcon,
  FolderPlusIcon,
  MessageIcon,
  PlusIcon,
  SearchIcon,
  SettingsIcon,
  SidebarIcon,
  UserIcon,
} from "@/components/ui/icons";

export const CHATS_CHANGED_EVENT = "chats:changed";

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
  const [query, setQuery] = useState("");
  const [chats, setChats] = useState<ChatListItem[]>([]);
  const [loadingChats, setLoadingChats] = useState(true);
  const [chatsError, setChatsError] = useState<string | null>(null);

  const refreshChats = useCallback(() => {
    let cancelled = false;
    setLoadingChats(true);
    setChatsError(null);
    getChats()
      .then((items) => {
        if (!cancelled) setChats(items);
      })
      .catch((err) => {
        if (cancelled) return;
        const message =
          err instanceof ApiError
            ? err.message
            : err instanceof Error
              ? err.message
              : "Failed to load chats.";
        setChatsError(message);
      })
      .finally(() => {
        if (!cancelled) setLoadingChats(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const cleanup = refreshChats();
    return cleanup;
  }, [refreshChats]);

  useEffect(() => {
    const handler = () => {
      refreshChats();
    };
    window.addEventListener(CHATS_CHANGED_EVENT, handler);
    return () => window.removeEventListener(CHATS_CHANGED_EVENT, handler);
  }, [refreshChats]);

  const filteredChats = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return chats;
    return chats.filter((c) => c.title.toLowerCase().includes(q));
  }, [query, chats]);

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
            onClick={onCloseMobile}
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

        <ProjectsSection
          collapsed={collapsed}
          activePath={pathname}
          onCloseMobile={onCloseMobile}
        />

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
              {filteredChats.map((chat) => {
                const href = `/chat/${chat.id}`;
                const isActive = pathname === href;
                return (
                  <li key={chat.id}>
                    <Link
                      href={href}
                      onClick={onCloseMobile}
                      title={chat.title}
                      className={cn(
                        "flex items-center gap-2 rounded-md px-2 py-2 text-sm transition-colors",
                        isActive
                          ? "bg-[var(--accent)] text-[var(--accent-foreground)]"
                          : "text-[var(--foreground)] hover:bg-[var(--accent)]",
                        collapsed && "md:justify-center md:px-0",
                      )}
                    >
                      <MessageIcon className="h-4 w-4 shrink-0" />
                      <span
                        className={cn(
                          "truncate",
                          collapsed && "md:hidden",
                        )}
                      >
                        {chat.title}
                      </span>
                    </Link>
                  </li>
                );
              })}
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

        <SidebarFooter collapsed={collapsed} />
      </aside>
    </>
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

function SidebarHeader({
  collapsed,
  onToggleCollapsed,
  onCloseMobile,
}: {
  collapsed: boolean;
  onToggleCollapsed: () => void;
  onCloseMobile: () => void;
}) {
  return (
    <div
      className={cn(
        "flex h-14 items-center gap-2 border-b border-[var(--border)] px-3",
        collapsed && "md:justify-center md:px-2",
      )}
    >
      <span className={cn("text-sm font-semibold", collapsed && "md:hidden")}>
        AI Doc Assist
      </span>
      <button
        type="button"
        onClick={onToggleCollapsed}
        className={cn(
          "ml-auto hidden h-8 w-8 items-center justify-center rounded-md text-[var(--muted-foreground)] hover:bg-[var(--accent)] hover:text-[var(--foreground)] md:inline-flex",
          collapsed && "md:ml-0",
        )}
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        <SidebarIcon className="h-4 w-4" />
      </button>
      <button
        type="button"
        onClick={onCloseMobile}
        className="ml-auto inline-flex h-8 w-8 items-center justify-center rounded-md text-[var(--muted-foreground)] hover:bg-[var(--accent)] hover:text-[var(--foreground)] md:hidden"
        aria-label="Close sidebar"
      >
        <CloseIcon className="h-4 w-4" />
      </button>
    </div>
  );
}

function ProjectsSection({
  collapsed,
  activePath,
  onCloseMobile,
}: {
  collapsed: boolean;
  activePath: string;
  onCloseMobile: () => void;
}) {
  const projectsHref = "/projects";

  return (
    <div
      className={cn(
        "border-t border-[var(--border)] px-2 pt-3 pb-2",
        collapsed && "md:pt-2",
      )}
    >
      <div
        className={cn(
          "flex items-center justify-between px-2 pb-1.5",
          collapsed && "md:hidden",
        )}
      >
        <span className="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]">
          Projects
        </span>
        <Link
          href={projectsHref}
          onClick={onCloseMobile}
          className="inline-flex items-center gap-0.5 text-[11px] font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
        >
          View all
          <ChevronRightIcon className="h-3 w-3" />
        </Link>
      </div>

      <ul className="space-y-1">
        {DUMMY_PROJECTS.map((project) => {
          const href = `/projects/${project.id}`;
          const isActive = activePath === href;
          return (
            <li key={project.id} className={cn(collapsed && "md:hidden")}>
              <Link
                href={href}
                onClick={onCloseMobile}
                title={project.name}
                className={cn(
                  "flex items-center gap-2 rounded-md px-2 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-[var(--accent)] text-[var(--accent-foreground)]"
                    : "text-[var(--foreground)] hover:bg-[var(--accent)]",
                  collapsed && "md:justify-center md:px-0",
                )}
              >
                <FolderIcon className="h-4 w-4 shrink-0" />
                <span className={cn("truncate", collapsed && "md:hidden")}>
                  {project.name}
                </span>
              </Link>
            </li>
          );
        })}

        <li>
          <button
            type="button"
            title="New project"
            className={cn(
              "flex w-full items-center gap-2 rounded-md px-2 py-2 text-sm text-[var(--muted-foreground)] transition-colors hover:bg-[var(--accent)] hover:text-[var(--foreground)]",
              collapsed && "md:justify-center md:px-0",
            )}
          >
            <FolderPlusIcon className="h-5 w-5 shrink-0" />
            <span className={cn(collapsed && "md:hidden")}>New project</span>
          </button>
        </li>
      </ul>
    </div>
  );
}

function SidebarFooter({ collapsed }: { collapsed: boolean }) {
  const { user } = useAuth();
  return (
    <div className="border-t border-[var(--border)] p-2">
      <div
        className={cn(
          "flex items-center gap-2 rounded-md px-2 py-2",
          collapsed && "md:justify-center md:px-0",
        )}
      >
        <div className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-[var(--accent)] text-[var(--accent-foreground)]">
          <UserIcon className="h-4 w-4" />
        </div>
        <div
          className={cn(
            "min-w-0 flex-1 leading-tight",
            collapsed && "md:hidden",
          )}
        >
          <p className="truncate text-sm font-medium">
            {user?.name ?? "Guest"}
          </p>
          {user && (
            <p className="truncate text-xs text-[var(--muted-foreground)]">
              Signed in
            </p>
          )}
        </div>
        <button
          type="button"
          className={cn(
            "inline-flex h-8 w-8 items-center justify-center rounded-md text-[var(--muted-foreground)] hover:bg-[var(--accent)] hover:text-[var(--foreground)]",
            collapsed && "md:hidden",
          )}
          aria-label="Settings"
        >
          <SettingsIcon className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
