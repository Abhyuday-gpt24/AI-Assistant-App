import { useCallback, useEffect, useState } from "react";
import { getProjects, type Project } from "@/lib/api/projects";
import { errorMessage } from "@/lib/api/error-message";
import { PROJECTS_CHANGED_EVENT } from "@/lib/events";

export type ProjectsState = {
  projects: Project[];
  loading: boolean;
  error: string | null;
};

// Loads the user's projects and refreshes on the projects:changed event (fired
// after a create / rename / delete). Same shape as the sidebar's useChats so both
// the sidebar ProjectsSection and the /projects grid can share it.
export function useProjects(): ProjectsState {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch + reconcile state ONLY in the async callbacks (never synchronously),
  // so the mount/refresh effects don't trip the set-state-in-effect lint rule.
  // `loading` starts true and is cleared once the first load settles; a
  // re-fetch (on projects:changed) swaps the data in place without a spinner.
  const load = useCallback((flag: { cancelled: boolean }) => {
    getProjects()
      .then((items) => {
        if (flag.cancelled) return;
        setProjects(items);
        setError(null);
      })
      .catch((err) => {
        if (!flag.cancelled) setError(errorMessage(err, "Failed to load projects."));
      })
      .finally(() => {
        if (!flag.cancelled) setLoading(false);
      });
  }, []);

  useEffect(() => {
    const flag = { cancelled: false };
    load(flag);
    return () => {
      flag.cancelled = true;
    };
  }, [load]);

  useEffect(() => {
    const handler = () => load({ cancelled: false });
    window.addEventListener(PROJECTS_CHANGED_EVENT, handler);
    return () => window.removeEventListener(PROJECTS_CHANGED_EVENT, handler);
  }, [load]);

  return { projects, loading, error };
}
