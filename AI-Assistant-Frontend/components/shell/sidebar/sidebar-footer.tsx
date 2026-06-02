import { cn } from "@/lib/cn";
import { SettingsIcon, UserIcon } from "@/components/ui/icons";
import { useAuth } from "@/components/auth/auth-provider";

export function SidebarFooter({ collapsed }: { collapsed: boolean }) {
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
