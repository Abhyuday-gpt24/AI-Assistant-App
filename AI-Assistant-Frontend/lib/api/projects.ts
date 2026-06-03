import { apiFetch, parseError } from "./client";
import type { ChatListItem } from "./chats";

// A project groups related chats over ONE shared RAG corpus: its `id` is the
// vector-store namespace every document uploaded in any of its chats lands in,
// so all of the project's chats retrieve over the same knowledge base.
export type Project = {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
};

export async function getProjects(): Promise<Project[]> {
  const res = await apiFetch("/api/projects");
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as Project[];
}

export async function getProject(id: string): Promise<Project> {
  const res = await apiFetch(`/api/projects/${encodeURIComponent(id)}`);
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as Project;
}

// Create a project from a name + description. The returned `id` is generated
// server-side and becomes the shared RAG namespace for the project's chats.
export async function createProject(
  name: string,
  description: string,
): Promise<Project> {
  const res = await apiFetch("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description }),
  });
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as Project;
}

export async function updateProject(
  id: string,
  patch: { name?: string; description?: string },
): Promise<Project> {
  const res = await apiFetch(`/api/projects/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as Project;
}

// The chats that live inside a project (these are filtered OUT of GET /api/chats,
// so the sidebar "Recent" list shows standalone chats only).
export async function getProjectChats(id: string): Promise<ChatListItem[]> {
  const res = await apiFetch(`/api/projects/${encodeURIComponent(id)}/chats`);
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as ChatListItem[];
}

// Delete a project and everything its chats share — the shared Pinecone
// namespace, all the uploaded S3 files, every chat (messages + checkpointer
// thread + attachment records), and the project itself (all server-side).
export async function deleteProject(id: string): Promise<void> {
  const res = await apiFetch(`/api/projects/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw await parseError(res);
}
