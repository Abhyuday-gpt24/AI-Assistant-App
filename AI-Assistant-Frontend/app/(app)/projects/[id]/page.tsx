import { notFound } from "next/navigation";
import { DUMMY_PROJECTS } from "@/lib/projects";
import { FolderIcon } from "@/components/ui/icons";

export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const project = DUMMY_PROJECTS.find((p) => p.id === id);
  if (!project) notFound();

  return (
    <div className="mx-auto w-full max-w-3xl px-3 py-6 sm:px-4">
      <div className="mb-6 flex items-center gap-3 border-b border-[var(--border)] pb-4">
        <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--accent)] text-[var(--accent-foreground)]">
          <FolderIcon className="h-4 w-4" />
        </span>
        <div>
          <h2 className="text-base font-semibold">{project.name}</h2>
          <p className="mt-0.5 text-sm text-[var(--muted-foreground)]">
            Project workspace
          </p>
        </div>
      </div>
      <p className="text-sm text-[var(--muted-foreground)]">
        Chats and documents in this project will appear here.
      </p>
    </div>
  );
}
