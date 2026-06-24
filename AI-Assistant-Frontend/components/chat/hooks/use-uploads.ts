import { useCallback, useEffect, useState } from "react";
import {
  uploadFile,
  triggerIngestion,
  getIngestionStatus,
} from "@/lib/api/uploads";
import type { AttachedFile } from "../chatbox";
import {
  buildUploadEntries,
  toAttachedFile,
  toReadyAttachments,
  type ReadyAttachments,
  type Upload,
} from "./upload-state";

export type { ReadyAttachments };

export type UploadsApi = {
  attachedFiles: AttachedFile[];
  hasUploading: boolean;
  addFiles: (files: File[]) => void;
  removeAttachment: (id: string) => void;
  getReady: () => ReadyAttachments;
  reset: () => void;
};

// Owns the attachment lifecycle for a chat: validate → presign+PUT to S3 →
// trigger RAG ingestion for documents → poll ingestion status. `chatIdRef` is
// always set (client-generated), so uploads + ingestion are scoped to this chat.
export function useUploads(
  chatIdRef: React.RefObject<string | undefined>,
): UploadsApi {
  const [uploads, setUploads] = useState<Upload[]>([]);

  // Step 2: files were just attached. Validate + show them as "uploading", then
  // presign + PUT each straight to S3 and stash the returned storage_path so
  // Send can reuse it without re-uploading.
  const addFiles = useCallback(
    (files: File[]) => {
      // Validate OUTSIDE the setUploads updater: React 19 StrictMode invokes
      // updaters twice in dev, and the uploads fired below must run exactly once.
      const entries = buildUploadEntries(files, uploads.length);
      setUploads((prev) => [...prev, ...entries]);

      // The reconciling setUploads calls below are pure (idempotent maps), so a
      // StrictMode double-invoke of them is harmless.
      for (const entry of entries) {
        if (entry.status !== "uploading") continue;
        uploadFile(entry.file, chatIdRef.current as string)
          .then((uploaded) => {
            const isDoc = uploaded.category === "docs";
            setUploads((cur) =>
              cur.map((u) =>
                u.id === entry.id
                  ? {
                      ...u,
                      status: "uploaded",
                      storagePath: uploaded.storagePath,
                      category: uploaded.category,
                      // Docs begin indexing immediately; the poll effect below
                      // flips this to "ready"/"error".
                      ingestStatus: isDoc ? "indexing" : undefined,
                    }
                  : u,
              ),
            );
            // Step 5 trigger: documents get converted + embedded into THIS
            // chat's RAG namespace (chatIdRef is always set) now that they're in
            // S3. Images are skipped (sent to the model inline at send time).
            if (isDoc) {
              triggerIngestion(
                chatIdRef.current as string,
                [
                  {
                    storage_path: uploaded.storagePath,
                    original_name: entry.name,
                    content_type: uploaded.contentType,
                  },
                ],
              ).catch(() => {
                // Couldn't even enqueue → mark errored so the chip isn't stuck.
                setUploads((cur) =>
                  cur.map((u) =>
                    u.id === entry.id ? { ...u, ingestStatus: "error" } : u,
                  ),
                );
              });
            }
          })
          .catch((err: unknown) => {
            const message =
              err instanceof Error ? err.message : "Upload failed";
            setUploads((cur) =>
              cur.map((u) =>
                u.id === entry.id ? { ...u, status: "error", error: message } : u,
              ),
            );
          });
      }
    },
    [uploads, chatIdRef],
  );

  const removeAttachment = useCallback((id: string) => {
    setUploads((prev) => prev.filter((u) => u.id !== id));
  }, []);

  // Poll ingestion status while any document is still "indexing". The key is a
  // stable join of the indexing paths, so the loop restarts when that set
  // changes (a doc turning ready/error drops out and the loop shrinks).
  const indexingKey = uploads
    .filter((u) => u.ingestStatus === "indexing" && u.storagePath)
    .map((u) => u.storagePath as string)
    .sort()
    .join("|");

  useEffect(() => {
    if (!indexingKey) return;
    const paths = indexingKey.split("|");
    let cancelled = false;
    let timer: number | undefined;

    const tick = async () => {
      try {
        const statuses = await getIngestionStatus(paths);
        if (cancelled) return;
        setUploads((cur) =>
          cur.map((u) => {
            if (u.ingestStatus !== "indexing" || !u.storagePath) return u;
            const s = statuses.find((x) => x.storage_path === u.storagePath);
            if (!s) return u;
            if (s.status === "ready") return { ...u, ingestStatus: "ready" };
            if (s.status === "error")
              return { ...u, ingestStatus: "error", error: s.error ?? "Indexing failed" };
            return u; // pending/processing → keep polling
          }),
        );
      } catch {
        // transient network/error — keep polling
      }
      if (!cancelled) timer = window.setTimeout(tick, 2500);
    };

    timer = window.setTimeout(tick, 1500);
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [indexingKey]);

  const attachedFiles = uploads.map(toAttachedFile);
  const hasUploading = uploads.some((u) => u.status === "uploading");
  const getReady = useCallback(() => toReadyAttachments(uploads), [uploads]);
  const reset = useCallback(() => setUploads([]), []);

  return {
    attachedFiles,
    hasUploading,
    addFiles,
    removeAttachment,
    getReady,
    reset,
  };
}
