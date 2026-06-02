import Link from "next/link";
import { cn } from "@/lib/cn";
import { DUMMY_PROJECTS } from "@/lib/projects";
import {
  ChevronRightIcon,
  FolderIcon,
  FolderPlusIcon,
} from "@/components/ui/icons";

export function ProjectsSection({
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
