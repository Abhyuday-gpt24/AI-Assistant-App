import { cn } from "@/lib/cn";
import { CloseIcon, SidebarIcon } from "@/components/ui/icons";

export function SidebarHeader({
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
