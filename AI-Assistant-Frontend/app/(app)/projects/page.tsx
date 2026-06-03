"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { FolderIcon, FolderPlusIcon } from "@/components/ui/icons";
import { Button } from "@/components/ui/button";
import { NewProjectDialog } from "@/components/projects/new-project-dialog";
import { useProjects } from "@/components/projects/use-projects";

export default function ProjectsPage() {
  const router = useRouter();
  const { projects, loading, error } = useProjects();
  const [creating, setCreating] = useState(false);

  return (
    <div className="mx-auto w-full max-w-3xl px-3 py-6 sm:px-4">
      <div className="mb-6 flex items-start justify-between gap-4 border-b border-[var(--border)] pb-4">
        <div>
          <h2 className="text-base font-semibold">Projects</h2>
          <p className="mt-1 text-sm text-[var(--muted-foreground)]">
            Group related chats so they share one set of uploaded documents.
          </p>
        </div>
        <Button size="sm" onClick={() => setCreating(true)}>
          <FolderPlusIcon className="h-4 w-4" />
          New project
        </Button>
      </div>

      {loading ? (
        <ul className="grid gap-3 sm:grid-cols-2" aria-busy="true">
          {[0, 1, 2, 3].map((i) => (
            <li
              key={i}
              className="h-20 animate-pulse rounded-xl border border-[var(--border)] bg-[var(--muted)]"
            />
          ))}
        </ul>
      ) : error ? (
        <p role="alert" className="text-sm text-[var(--muted-foreground)]">
          {error}
        </p>
      ) : projects.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[var(--border)] p-8 text-center">
          <p className="text-sm text-[var(--muted-foreground)]">
            No projects yet. Create one to share documents across a set of chats.
          </p>
          <Button size="sm" className="mt-4" onClick={() => setCreating(true)}>
            <FolderPlusIcon className="h-4 w-4" />
            New project
          </Button>
        </div>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {projects.map((project) => (
            <li key={project.id}>
              <Link
                href={`/projects/${project.id}`}
                className="flex h-full items-start gap-3 rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 transition-colors hover:bg-[var(--accent)]"
              >
                <span className="mt-0.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--accent)] text-[var(--accent-foreground)]">
                  <FolderIcon className="h-4 w-4" />
                </span>
                <span className="min-w-0">
                  <span className="block truncate text-sm font-medium">
                    {project.name}
                  </span>
                  {project.description && (
                    <span className="mt-0.5 block line-clamp-2 text-xs text-[var(--muted-foreground)]">
                      {project.description}
                    </span>
                  )}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}

      <NewProjectDialog
        open={creating}
        onClose={() => setCreating(false)}
        onCreated={(project) => router.push(`/projects/${project.id}`)}
      />
    </div>
  );
}
