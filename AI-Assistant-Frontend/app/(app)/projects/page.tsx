import Link from "next/link";
import { DUMMY_PROJECTS } from "@/lib/projects";
import { FolderIcon } from "@/components/ui/icons";

export default function ProjectsPage() {
  return (
    <div className="mx-auto w-full max-w-3xl px-3 py-6 sm:px-4">
      <div className="mb-6 border-b border-[var(--border)] pb-4">
        <h2 className="text-base font-semibold">Projects</h2>
        <p className="mt-1 text-sm text-[var(--muted-foreground)]">
          Group related chats and documents together.
        </p>
      </div>
      <ul className="grid gap-3 sm:grid-cols-2">
        {DUMMY_PROJECTS.map((project) => (
          <li key={project.id}>
            <Link
              href={`/projects/${project.id}`}
              className="flex items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 transition-colors hover:bg-[var(--accent)]"
            >
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--accent)] text-[var(--accent-foreground)]">
                <FolderIcon className="h-4 w-4" />
              </span>
              <span className="text-sm font-medium">{project.name}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
