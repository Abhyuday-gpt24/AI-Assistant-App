import { useCallback, useEffect, useState } from "react";
import { getProject, getProjectChats, type Project } from "@/lib/api/projects";
import type { ChatListItem } from "@/lib/api/chats";
import { errorMessage } from "@/lib/api/error-message";
import { CHATS_CHANGED_EVENT, PROJECTS_CHANGED_EVENT } from "@/lib/events";

export type ProjectDetailState = {
  project: Project | null;
  chats: ChatListItem[];
  loading: boolean;
  error: string | null;
};

// Loads one project's metadata + its chats together. Refetches the chat list on
// chats:changed (a project chat being created/deleted fires it) and the project
// metadata on projects:changed (a rename). Keeps the project detail view live
// without prop-drilling refresh callbacks.
export function useProjectDetail(projectId: string): ProjectDetailState {
  const [project, setProject] = useState<Project | null>(null);
  const [chats, setChats] = useState<ChatListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // All state updates live in async callbacks (never synchronously in the
  // effect), so the loader doesn't trip the set-state-in-effect lint rule.
  const load = useCallback(
    (flag: { cancelled: boolean }) => {
      Promise.all([getProject(projectId), getProjectChats(projectId)])
        .then(([p, c]) => {
          if (flag.cancelled) return;
          setProject(p);
          setChats(c);
          setError(null);
        })
        .catch((err) => {
          if (!flag.cancelled) setError(errorMessage(err, "Failed to load project."));
        })
        .finally(() => {
          if (!flag.cancelled) setLoading(false);
        });
    },
    [projectId],
  );

  useEffect(() => {
    const flag = { cancelled: false };
    load(flag);
    return () => {
      flag.cancelled = true;
    };
  }, [load]);

  // Refresh just the chat list when chats change (cheap, no full-page spinner).
  useEffect(() => {
    const onChats = () => {
      getProjectChats(projectId)
        .then(setChats)
        .catch(() => {
          /* keep the stale list on a transient error */
        });
    };
    window.addEventListener(CHATS_CHANGED_EVENT, onChats);
    window.addEventListener(PROJECTS_CHANGED_EVENT, onChats);
    return () => {
      window.removeEventListener(CHATS_CHANGED_EVENT, onChats);
      window.removeEventListener(PROJECTS_CHANGED_EVENT, onChats);
    };
  }, [projectId]);

  return { project, chats, loading, error };
}
