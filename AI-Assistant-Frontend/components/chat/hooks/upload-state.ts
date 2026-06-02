import {
  ALLOWED_UPLOAD_TYPES,
  MAX_FILES_PER_MESSAGE,
  type Attachment,
} from "@/lib/api/uploads";
import type { AttachedFile } from "../chatbox";
import type { MessageAttachment } from "../types";
import { randomUUID } from "@/lib/uuid";

// Internal, richer shape than the Chatbox's display-only AttachedFile: it keeps
// the File and the storage_path we get back from S3 so send() can reuse it.
// ingestStatus tracks the RAG indexing of a *document* after it's uploaded.
export type Upload = {
  id: string;
  name: string;
  file: File;
  status: "uploading" | "uploaded" | "error";
  storagePath?: string;
  category?: "images" | "docs";
  ingestStatus?: "indexing" | "ready" | "error";
  error?: string;
};

const ALLOWED_SET = new Set<string>(ALLOWED_UPLOAD_TYPES);

// Files that finished uploading carry a storage_path we can send: the chat
// endpoint payload plus the display-only projection for the user's bubble.
export type ReadyAttachments = {
  attachments: Attachment[];
  bubbleAttachments: MessageAttachment[];
};

// Validate newly attached files against type + count limits, producing the
// initial Upload entries. Rejected files become "error" entries (so the user
// sees why); accepted ones start as "uploading". Pure so it can run outside a
// setState updater — React 19 StrictMode double-invokes updaters in dev, and a
// presign+upload fired from inside one would run twice.
export function buildUploadEntries(
  files: File[],
  existingCount: number,
): Upload[] {
  const entries: Upload[] = [];
  let count = existingCount;
  for (const file of files) {
    const id = randomUUID();
    if (!ALLOWED_SET.has(file.type)) {
      entries.push({
        id,
        name: file.name,
        file,
        status: "error",
        error: `Unsupported file type: ${file.type || "unknown"}`,
      });
      continue;
    }
    if (count >= MAX_FILES_PER_MESSAGE) {
      entries.push({
        id,
        name: file.name,
        file,
        status: "error",
        error: `Max ${MAX_FILES_PER_MESSAGE} files per message`,
      });
      continue;
    }
    count++;
    entries.push({ id, name: file.name, file, status: "uploading" });
  }
  return entries;
}

// Display-only projection handed to the Chatbox.
export function toAttachedFile(u: Upload): AttachedFile {
  return {
    id: u.id,
    name: u.name,
    status: u.status,
    ingestStatus: u.ingestStatus,
    error: u.error,
  };
}

// Collect the files that finished uploading into the shapes send() needs.
export function toReadyAttachments(uploads: Upload[]): ReadyAttachments {
  const ready = uploads.filter((u) => u.status === "uploaded" && u.storagePath);
  return {
    attachments: ready.map((u) => ({
      original_name: u.name,
      storage_path: u.storagePath as string,
    })),
    bubbleAttachments: ready.map((u) => ({
      name: u.name,
      storagePath: u.storagePath as string,
    })),
  };
}
