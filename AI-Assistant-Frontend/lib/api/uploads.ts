import { apiFetch, parseError } from "./client";

// Standalone images: streamed to the chat model inline (base64), NOT ingested.
export const IMAGE_UPLOAD_TYPES = [
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/gif",
] as const;

// Documents: converted to Markdown + embedded into the user's RAG namespace.
export const DOC_UPLOAD_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document", // docx
  "application/vnd.openxmlformats-officedocument.presentationml.presentation", // pptx
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", // xlsx
  "application/epub+zip", // epub
  "text/plain",
  "text/html",
  "text/csv",
  "text/markdown",
] as const;

// Keep in sync with the backend (s3_bucket_service.py ALLOWED_TYPES).
export const ALLOWED_UPLOAD_TYPES = [
  ...IMAGE_UPLOAD_TYPES,
  ...DOC_UPLOAD_TYPES,
] as const;
export const MAX_FILES_PER_MESSAGE = 10;

const IMAGE_SET = new Set<string>(IMAGE_UPLOAD_TYPES);

// Extension → MIME fallback for when the browser leaves file.type blank
// (common for .docx/.pptx/.epub). Without this, the presign call 415s.
const EXT_TO_TYPE: Record<string, string> = {
  pdf: "application/pdf",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  pptx: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  epub: "application/epub+zip",
  txt: "text/plain",
  md: "text/markdown",
  html: "text/html",
  htm: "text/html",
  csv: "text/csv",
  png: "image/png",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  webp: "image/webp",
  gif: "image/gif",
};

/** The file's MIME type, falling back to its extension when the browser omits one. */
export function resolveContentType(file: File): string {
  if (file.type) return file.type;
  const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
  return EXT_TO_TYPE[ext] ?? "";
}

export function isImageType(contentType: string): boolean {
  return IMAGE_SET.has(contentType);
}

// What the chat endpoint needs to know about each attached file.
export type Attachment = {
  original_name: string;
  storage_path: string;
};

// The result of uploading one file — enough to send with the chat message AND
// to trigger ingestion for documents.
export type UploadedFile = {
  storagePath: string;
  contentType: string;
  category: "images" | "docs";
};

type PresignedEntry = {
  original_name: string;
  storage_path: string;
  upload_url: string;
  content_type: string;
  category: "images" | "docs";
  expires_in: number;
};

type PresignedResponse = {
  urls: PresignedEntry[];
  total: number;
};

// Step 2 (NO branch): ask the backend for presigned PUT URLs for files that
// don't have a storage_path yet. The backend mints a unique, user-scoped,
// type-routed S3 key (images/ vs docs/) per file.
export async function getPresignedUrls(
  files: { name: string; content_type: string }[],
  folder = "attachments",
): Promise<PresignedEntry[]> {
  const res = await apiFetch(
    `/api/storage/upload/presigned?folder=${encodeURIComponent(folder)}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(files),
    },
  );
  if (!res.ok) throw await parseError(res);
  const data = (await res.json()) as PresignedResponse;
  return data.urls;
}

// Upload the bytes DIRECTLY to S3 with the presigned PUT URL. This bypasses
// apiFetch on purpose: the URL is absolute (Supabase/S3, not our backend), it
// must NOT carry our session cookie, and the Content-Type must match exactly
// what was signed or S3 rejects the signature.
export async function uploadToS3(
  uploadUrl: string,
  file: File,
  contentType: string,
): Promise<void> {
  const res = await fetch(uploadUrl, {
    method: "PUT",
    headers: { "Content-Type": contentType },
    body: file,
  });
  if (!res.ok) {
    throw new Error(`Upload failed (${res.status} ${res.statusText})`);
  }
}

// Convenience: presign + upload a single file, returning where it landed.
export async function uploadFile(file: File): Promise<UploadedFile> {
  const contentType = resolveContentType(file);
  const [entry] = await getPresignedUrls([
    { name: file.name, content_type: contentType },
  ]);
  if (!entry) throw new Error("No presigned URL returned for file.");
  await uploadToS3(entry.upload_url, file, entry.content_type);
  return {
    storagePath: entry.storage_path,
    contentType: entry.content_type,
    category: entry.category,
  };
}

// Step 5 trigger: once a document has finished uploading to S3, tell the backend
// to convert + embed it into this chat's RAG namespace. The backend resolves the
// namespace: a standalone chat uses its own chat_id (retrieves only its own
// files); a project chat uses the project's shared corpus. `projectId` is passed
// so a brand-new project chat (not yet persisted) is seeded into the project
// namespace before its first message. Runs server-side in a background task, so
// this returns quickly. Images are skipped (sent inline).
export async function triggerIngestion(
  chatId: string,
  files: { storage_path: string; original_name: string; content_type: string }[],
  projectId?: string,
): Promise<void> {
  if (files.length === 0) return;
  const res = await apiFetch("/api/ingestion/process", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      ...(projectId ? { project_id: projectId } : {}),
      files,
    }),
  });
  if (!res.ok) throw await parseError(res);
}

export type IngestionStatus = {
  storage_path: string;
  status: "pending" | "processing" | "ready" | "error";
  method?: string | null;
  chunks?: number;
  error?: string | null;
};

// Poll the status of in-flight ingestion jobs (background conversion+embedding).
// Caller-scoped server-side; returns only rows that exist for these paths.
export async function getIngestionStatus(
  storagePaths: string[],
): Promise<IngestionStatus[]> {
  if (storagePaths.length === 0) return [];
  const params = new URLSearchParams();
  for (const p of storagePaths) params.append("storage_paths", p);
  const res = await apiFetch(`/api/ingestion/status?${params.toString()}`);
  if (!res.ok) throw await parseError(res);
  const data = (await res.json()) as { statuses: IngestionStatus[] };
  return data.statuses;
}
