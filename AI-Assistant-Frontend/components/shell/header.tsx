"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { LogoutIcon, MenuIcon } from "@/components/ui/icons";
import { logout } from "@/lib/api/auth";
import { useAuth } from "@/components/auth/auth-provider";

type HeaderProps = {
  onOpenMobile: () => void;
  title: string;
};

export function Header({ onOpenMobile, title }: HeaderProps) {
  const router = useRouter();
  const { setUser } = useAuth();
  const [signingOut, setSigningOut] = useState(false);

  async function handleSignOut() {
    if (signingOut) return;
    setSigningOut(true);
    try {
      await logout();
    } catch {
      // even if the backend call fails, route to /login so the user can re-auth
    }
    setUser(null);
    router.push("/login");
  }

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-2 border-b border-[var(--border)] bg-[var(--background)]/80 px-3 backdrop-blur sm:px-4">
      <button
        type="button"
        onClick={onOpenMobile}
        className="inline-flex h-9 w-9 items-center justify-center rounded-md text-[var(--muted-foreground)] hover:bg-[var(--accent)] hover:text-[var(--foreground)] md:hidden"
        aria-label="Open sidebar"
      >
        <MenuIcon className="h-5 w-5" />
      </button>
      <h1 className="truncate text-sm font-semibold">{title}</h1>
      <div className="ml-auto flex items-center gap-2">
        <ThemeToggle />
        <button
          type="button"
          onClick={handleSignOut}
          disabled={signingOut}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md text-[var(--muted-foreground)] hover:bg-[var(--accent)] hover:text-[var(--foreground)] disabled:opacity-50"
          aria-label="Sign out"
        >
          <LogoutIcon className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
