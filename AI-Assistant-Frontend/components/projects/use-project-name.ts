import { useEffect, useState } from "react";
import { getProject } from "@/lib/api/projects";
import { PROJECTS_CHANGED_EVENT } from "@/lib/events";

// Module-level cache of project id → name. The header (and anything that only
// needs a project's display name) reads from here, so navigating between a
// project's chats doesn't refetch. Invalidated on projects:changed (a rename).
const nameCache = new Map<string, string>();

/**
 * The display name for a project id, or null while unknown. Resolves from the
 * module cache first (instant on repeat navigations), else fetches once. Pass
 * `undefined` (e.g. on a non-project route) to get null.
 *
 * Lint-safe: the synchronous reset on a projectId change happens DURING render
 * (the React-recommended alternative to a prop-syncing effect); the effect only
 * sets state inside an async callback.
 */
export function useProjectName(projectId?: string): string | null {
  const initial = projectId ? (nameCache.get(projectId) ?? null) : null;
  const [name, setName] = useState<string | null>(initial);

  // Re-seed from the cache (or null) when the project changes — during render.
  const [trackedId, setTrackedId] = useState(projectId);
  if (trackedId !== projectId) {
    setTrackedId(projectId);
    setName(projectId ? (nameCache.get(projectId) ?? null) : null);
  }

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;

    const sync = () => {
      getProject(projectId)
        .then((p) => {
          if (cancelled) return;
          nameCache.set(projectId, p.name);
          setName(p.name);
        })
        .catch(() => {
          /* keep whatever we have (cache or null) on a transient error */
        });
    };

    sync(); // refetch to stay fresh (cache already seeded the initial render)
    // A rename fires projects:changed — re-resolve the name.
    window.addEventListener(PROJECTS_CHANGED_EVENT, sync);
    return () => {
      cancelled = true;
      window.removeEventListener(PROJECTS_CHANGED_EVENT, sync);
    };
  }, [projectId]);

  return name;
}
