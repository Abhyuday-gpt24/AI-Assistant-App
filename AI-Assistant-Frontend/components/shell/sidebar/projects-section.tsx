"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { cn } from "@/lib/cn";
import {
  ChevronRightIcon,
  FolderIcon,
  FolderPlusIcon,
} from "@/components/ui/icons";
import { NewProjectDialog } from "@/components/projects/new-project-dialog";
import { useProjects } from "@/components/projects/use-projects";

// How many projects to surface inline in the sidebar before "View all".
const MAX_INLINE_PROJECTS = 6;

export function ProjectsSection({
  collapsed,
  activePath,
  onCloseMobile,
}: {
  collapsed: boolean;
  activePath: string;
  onCloseMobile: () => void;
}) {
  const router = useRouter();
  const { projects, loading } = useProjects();
  const [creating, setCreating] = useState(false);

  const inlineProjects = projects.slice(0, MAX_INLINE_PROJECTS);

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
          href="/projects"
          onClick={onCloseMobile}
          className="inline-flex items-center gap-0.5 text-[11px] font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
        >
          View all
          <ChevronRightIcon className="h-3 w-3" />
        </Link>
      </div>

      <ul className="space-y-1">
        {!loading &&
          inlineProjects.map((project) => {
            // A project is active when we're anywhere inside it (its page or one
            // of its chats: /projects/{id} or /projects/{id}/chat/...).
            const base = `/projects/${project.id}`;
            const isActive =
              activePath === base || activePath.startsWith(`${base}/`);
            return (
              <li key={project.id} className={cn(collapsed && "md:hidden")}>
                <Link
                  href={base}
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

        {!loading && projects.length === 0 && (
          <li className={cn("px-2 py-1.5", collapsed && "md:hidden")}>
            <p className="text-xs text-[var(--muted-foreground)]">
              No projects yet.
            </p>
          </li>
        )}

        <li>
          <button
            type="button"
            title="New project"
            onClick={() => setCreating(true)}
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

      <NewProjectDialog
        open={creating}
        onClose={() => setCreating(false)}
        onCreated={(project) => {
          onCloseMobile();
          router.push(`/projects/${project.id}`);
        }}
      />
    </div>
  );
}
