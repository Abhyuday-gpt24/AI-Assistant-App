"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";
import { cn } from "@/lib/cn";
import {
  FolderIcon,
  MessageIcon,
  PlusIcon,
  TrashIcon,
  SpinnerIcon,
} from "@/components/ui/icons";
import { Button } from "@/components/ui/button";
import { useDialog } from "@/components/ui/dialog";
import { deleteChat } from "@/lib/api/chats";
import { deleteProject } from "@/lib/api/projects";
import { emitChatsChanged, emitProjectsChanged } from "@/lib/events";
import { errorMessage } from "@/lib/api/error-message";
import { useProjectDetail } from "./use-project-detail";

export function ProjectDetail({ projectId }: { projectId: string }) {
  const router = useRouter();
  const { confirm, alert } = useDialog();
  const { project, chats, loading, error } = useProjectDetail(projectId);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deletingProject, setDeletingProject] = useState(false);

  // Delete a single chat in the project (its own messages/checkpointer only —
  // the shared corpus stays, server-side). Refresh the list via chats:changed.
  const handleDeleteChat = useCallback(
    async (id: string, title: string) => {
      const ok = await confirm({
        title: "Delete chat",
        message: `Delete "${title}"? The project's shared documents are kept.`,
        confirmLabel: "Delete",
        variant: "danger",
      });
      if (!ok) return;
      setDeletingId(id);
      try {
        await deleteChat(id);
        emitChatsChanged();
      } catch (err) {
        await alert({
          title: "Delete failed",
          message: errorMessage(err, "Couldn't delete the chat."),
        });
      } finally {
        setDeletingId(null);
      }
    },
    [confirm, alert],
  );

  // Delete the whole project: its shared namespace + all files + every chat.
  const handleDeleteProject = useCallback(async () => {
    const ok = await confirm({
      title: "Delete project",
      message:
        "Delete this project, all of its chats, and the documents they share? This can't be undone.",
      confirmLabel: "Delete project",
      variant: "danger",
    });
    if (!ok) return;
    setDeletingProject(true);
    try {
      await deleteProject(projectId);
      emitProjectsChanged();
      emitChatsChanged();
      router.push("/projects");
    } catch (err) {
      setDeletingProject(false);
      await alert({
        title: "Delete failed",
        message: errorMessage(err, "Couldn't delete the project."),
      });
    }
  }, [confirm, alert, projectId, router]);

  if (loading) {
    return (
      <div className="mx-auto w-full max-w-3xl px-3 py-6 sm:px-4">
        <div className="h-20 animate-pulse rounded-xl border border-[var(--border)] bg-[var(--muted)]" />
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="mx-auto w-full max-w-3xl px-3 py-6 sm:px-4">
        <p role="alert" className="text-sm text-[var(--muted-foreground)]">
          {error ?? "Project not found."}
        </p>
        <Link
          href="/projects"
          className="mt-3 inline-block text-sm text-[var(--primary)] hover:underline"
        >
          Back to projects
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-3xl px-3 py-6 sm:px-4">
      <div className="mb-6 flex items-start justify-between gap-4 border-b border-[var(--border)] pb-4">
        <div className="flex min-w-0 items-start gap-3">
          <span className="mt-0.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--accent)] text-[var(--accent-foreground)]">
            <FolderIcon className="h-4 w-4" />
          </span>
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold">{project.name}</h2>
            <p className="mt-0.5 text-sm text-[var(--muted-foreground)]">
              {project.description || "Shared workspace for related chats."}
            </p>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleDeleteProject}
          disabled={deletingProject}
          className="shrink-0 text-[var(--muted-foreground)] hover:text-red-500"
        >
          {deletingProject ? (
            <SpinnerIcon className="h-4 w-4 animate-spin" />
          ) : (
            <TrashIcon className="h-4 w-4" />
          )}
          Delete
        </Button>
      </div>

      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-medium">Chats</h3>
        <Link
          href={`/projects/${projectId}/chat`}
          className="inline-flex items-center gap-1.5 rounded-md bg-[var(--primary)] px-3 py-1.5 text-sm font-medium text-[var(--primary-foreground)] hover:opacity-90"
        >
          <PlusIcon className="h-4 w-4" />
          New chat
        </Link>
      </div>

      {chats.length === 0 ? (
        <p className="rounded-xl border border-dashed border-[var(--border)] p-6 text-center text-sm text-[var(--muted-foreground)]">
          No chats yet. Start one — documents you attach here are shared across
          every chat in this project.
        </p>
      ) : (
        <ul className="space-y-1">
          {chats.map((chat) => (
            <li key={chat.id} className="group relative">
              <Link
                href={`/projects/${projectId}/chat/${chat.id}`}
                title={chat.title}
                className="flex items-center gap-2 rounded-md px-2 py-2 pr-9 text-sm text-[var(--foreground)] transition-colors hover:bg-[var(--accent)]"
              >
                <MessageIcon className="h-4 w-4 shrink-0" />
                <span className="truncate">{chat.title}</span>
              </Link>
              <button
                type="button"
                onClick={() => handleDeleteChat(chat.id, chat.title)}
                disabled={deletingId === chat.id}
                title="Delete chat"
                aria-label={`Delete chat ${chat.title}`}
                className={cn(
                  "absolute right-1 top-1/2 grid h-7 w-7 -translate-y-1/2 place-items-center rounded-md text-[var(--muted-foreground)] transition-opacity hover:bg-[var(--background)] hover:text-red-500 focus:outline-none focus:ring-2 focus:ring-[var(--ring)]/40",
                  deletingId === chat.id
                    ? "opacity-100"
                    : "opacity-0 focus-visible:opacity-100 group-hover:opacity-100",
                )}
              >
                {deletingId === chat.id ? (
                  <SpinnerIcon className="h-4 w-4 animate-spin" />
                ) : (
                  <TrashIcon className="h-4 w-4" />
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
