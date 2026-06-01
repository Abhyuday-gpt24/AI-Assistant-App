"use client";

import { useCallback, useState } from "react";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { Footer } from "./footer";

export function Shell({
  children,
  title,
}: {
  children: React.ReactNode;
  title: string;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const toggleCollapsed = useCallback(() => setCollapsed((c) => !c), []);
  const openMobile = useCallback(() => setMobileOpen(true), []);
  const closeMobile = useCallback(() => setMobileOpen(false), []);

  return (
    <div className="flex h-dvh w-full bg-[var(--background)] text-[var(--foreground)]">
      <Sidebar
        collapsed={collapsed}
        mobileOpen={mobileOpen}
        onToggleCollapsed={toggleCollapsed}
        onCloseMobile={closeMobile}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header onOpenMobile={openMobile} title={title} />
        <main className="flex min-h-0 flex-1 flex-col">{children}</main>
        <Footer />
      </div>
    </div>
  );
}
