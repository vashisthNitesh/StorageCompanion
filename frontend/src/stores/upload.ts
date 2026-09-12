import { defineStore } from "pinia";
import { ref, computed, reactive } from "vue";
import { apiRequest, getAccessToken } from "../lib/api";
import { useAuthStore } from "./auth";
import { useFilesStore } from "./files";
import { generateFileKey, generateRandomBytes, wrapKey } from "../lib/crypto/keys";
import { encryptName } from "../lib/crypto/names";
import { deriveChunkNonce, encryptChunk } from "../lib/crypto/content";
import {
  uint8ArrayToBase64,
  uint8ArrayToHex,
  hexToUint8Array,
} from "../lib/crypto/kdf";
import { saveUploadState, removeUploadState, type StoredUpload } from "../lib/db";

function uploadPartWithProgress(
  url: string,
  data: Uint8Array,
  method: "PUT" | "POST",
  headers: Record<string, string>,
  onProgress: (loaded: number, total: number) => void,
  timeoutMs: number = 60000
): Promise<{ ok: boolean; status: number; etag: string; responseJson?: any }> {
  return new Promise((resolve) => {
    const xhr = new XMLHttpRequest();
    xhr.open(method, url, true);
    xhr.timeout = timeoutMs;
    for (const [k, v] of Object.entries(headers)) {
      xhr.setRequestHeader(k, v);
    }
    xhr.withCredentials = true;

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        onProgress(e.loaded, e.total);
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        let responseJson: any = null;
        try {
          responseJson = JSON.parse(xhr.responseText);
        } catch {
          // not json
        }
        const etag = xhr.getResponseHeader("ETag") || responseJson?.etag || "";
        resolve({ ok: true, status: xhr.status, etag, responseJson });
      } else {
        resolve({ ok: false, status: xhr.status, etag: "" });
      }
    };

    xhr.onerror = () => resolve({ ok: false, status: 0, etag: "" });
    xhr.ontimeout = () => resolve({ ok: false, status: 408, etag: "" });
    xhr.onabort = () => resolve({ ok: false, status: 0, etag: "" });

    xhr.send(data);
  });
}

export interface ActiveUpload {
  id: string; // client temporary ID
  file: File;
  name: string;
  size: number;
  progress: number; // 0 to 100
  speedMBs: number;
  status: "queued" | "encrypting" | "uploading" | "completing" | "completed" | "error" | "paused";
  errorMessage?: string;
  uploadSessionId?: string;
  completedBytes: number;
}

export const useUploadStore = defineStore("upload", () => {
  const authStore = useAuthStore();
  const filesStore = useFilesStore();
  const uploads = ref<ActiveUpload[]>([]);
  const isTrayOpen = ref<boolean>(false);

  const activeCount = computed(
    () => uploads.value.filter((u) => u.status === "uploading" || u.status === "encrypting" || u.status === "completing").length
  );
  const totalProgress = computed(() => {
    if (uploads.value.length === 0) return 0;
    const sum = uploads.value.reduce((acc, u) => acc + u.progress, 0);
    return Math.round(sum / uploads.value.length);
  });

  async function uploadFile(file: File, parentId: string | null = null) {
    if (!authStore.masterKey) throw new Error("Vault must be unlocked to upload.");

    const uploadItem = reactive<ActiveUpload>({
      id: crypto.randomUUID(),
      file,
      name: file.name,
      size: file.size,
      progress: 0,
      speedMBs: 0,
      status: "queued",
      completedBytes: 0,
    });

    uploads.value.unshift(uploadItem);
    isTrayOpen.value = true;

    try {
      uploadItem.status = "encrypting";

      // 1. Generate per-file AES-256-GCM key and 12-byte base nonce
      const fileKey = generateFileKey();
      const baseNonce = generateRandomBytes(12);

      // 2. Wrap File Key with user's Master Key
      const wrappedFileKey = await wrapKey(authStore.masterKey, fileKey);

      // 3. Encrypt filename with Master Key
      const { ciphertextBase64, nonceHex } = await encryptName(
        authStore.masterKey,
        file.name
      );

      // 4. Request multipart upload from backend
      const initData = await apiRequest<{
        upload_session_id: string;
        s3_upload_id: string;
        object_key: string;
        part_size: number;
        total_parts: number;
        presigned_urls: { part_number: number; url: string }[];
      }>("/api/v1/uploads", {
        method: "POST",
        body: JSON.stringify({
          parent_id: parentId,
          encrypted_name: ciphertextBase64,
          name_nonce: nonceHex,
          size_bytes: file.size,
        }),
      });

      uploadItem.uploadSessionId = initData.upload_session_id;
      uploadItem.status = "uploading";

      const partSize = initData.part_size;
      const totalParts = initData.total_parts;
      const completedParts: { part_number: number; etag: string }[] = [];

      // Save initial state to IndexedDB for resumability
      const storedUpload: StoredUpload = {
        uploadSessionId: initData.upload_session_id,
        s3UploadId: initData.s3_upload_id,
        fileKeyHex: uint8ArrayToHex(fileKey),
        baseNonceHex: uint8ArrayToHex(baseNonce),
        wrappedFileKey,
        fileName: file.name,
        fileSize: file.size,
        partSize,
        totalParts,
        completedParts: [],
        status: "uploading",
      };
      await saveUploadState(storedUpload);

      // 5. Upload chunks with bounded concurrency (4 parallel streams)
      const concurrency = 4;
      let nextPartIndex = 0;
      let directUploadFailed = false;
      let totalCommittedBytes = 0;
      const inFlightBytes = new Map<number, number>();
      const startTime = Date.now();

      function updateProgress() {
        let activeInFlight = 0;
        for (const bytes of inFlightBytes.values()) {
          activeInFlight += bytes;
        }
        const currentBytes = Math.min(file.size, totalCommittedBytes + activeInFlight);
        uploadItem.completedBytes = currentBytes;
        uploadItem.progress = Math.min(99, Math.round((currentBytes / file.size) * 100));

        const elapsedSec = (Date.now() - startTime) / 1000;
        if (elapsedSec > 0.2) {
          uploadItem.speedMBs = Number((currentBytes / (1024 * 1024) / elapsedSec).toFixed(1));
        }
      }

      async function uploadNextPart(): Promise<void> {
        while (nextPartIndex < totalParts) {
          if (uploadItem.status === "paused") return;

          const partIndex = nextPartIndex++;
          const partNumber = partIndex + 1;
          const start = partIndex * partSize;
          const end = Math.min(file.size, start + partSize);
          const chunkBlob = file.slice(start, end);
          const chunkBuffer = await chunkBlob.arrayBuffer();
          const chunkBytes = new Uint8Array(chunkBuffer);

          // Encrypt chunk using AES-256-GCM with deterministic nonce: baseNonce ^ partNumber
          const encryptedChunk = await encryptChunk(
            fileKey,
            chunkBytes,
            baseNonce,
            partNumber
          );

          // Find presigned URL if available
          const presignedUrl = (!directUploadFailed && initData.presigned_urls)
            ? initData.presigned_urls.find((p: { part_number: number; url: string }) => p.part_number === partNumber)?.url
            : null;

          let retries = 3;
          let etag = "";
          let uploaded = false;

          while (retries > 0 && !uploaded) {
            // 1. Try direct upload if available and not previously failed
            if (presignedUrl && !directUploadFailed) {
              const directRes = await uploadPartWithProgress(
                presignedUrl,
                encryptedChunk,
                "PUT",
                { "Content-Type": "application/octet-stream" },
                (loaded) => {
                  inFlightBytes.set(partNumber, Math.min(chunkBytes.length, Math.round(loaded * (chunkBytes.length / encryptedChunk.length))));
                  updateProgress();
                },
                5000 // Fast 5s timeout to prevent long stalls if blocked by CORS or network
              );

              if (directRes.ok) {
                etag = directRes.etag || `"${partNumber}"`;
                uploaded = true;
                break;
              } else {
                // Direct upload failed or blocked by CORS: mark direct as unavailable
                directUploadFailed = true;
              }
            }

            // 2. Fallback: relay through backend API endpoint
            const token = getAccessToken();
            const relayHeaders: Record<string, string> = {
              "Content-Type": "application/octet-stream",
            };
            if (token) {
              relayHeaders["Authorization"] = `Bearer ${token}`;
            }

            const relayRes = await uploadPartWithProgress(
              `/api/v1/uploads/${initData.upload_session_id}/parts/${partNumber}`,
              encryptedChunk,
              "POST",
              relayHeaders,
              (loaded) => {
                inFlightBytes.set(partNumber, Math.min(chunkBytes.length, Math.round(loaded * (chunkBytes.length / encryptedChunk.length))));
                updateProgress();
              },
              60000
            );

            if (relayRes.ok) {
              etag = relayRes.etag || relayRes.responseJson?.etag || `"${partNumber}"`;
              uploaded = true;
              break;
            } else {
              retries--;
              if (retries === 0) throw new Error(`Failed to upload part ${partNumber}`);
              await new Promise((r) => setTimeout(r, 1000));
            }
          }

          inFlightBytes.delete(partNumber);
          totalCommittedBytes += chunkBytes.length;
          updateProgress();
          completedParts.push({ part_number: partNumber, etag });

          // Persist progress to IndexedDB
          storedUpload.completedParts = completedParts;
          await saveUploadState(storedUpload);
        }
      }

      const workers = Array.from({ length: concurrency }, () => uploadNextPart());
      await Promise.all(workers);

      if ((uploadItem.status as string) === "paused") return;

      // 6. Complete multipart upload on backend
      uploadItem.status = "completing";
      await apiRequest(`/api/v1/uploads/${initData.upload_session_id}/complete`, {
        method: "POST",
        body: JSON.stringify({
          parts: completedParts,
          wrapped_file_key: wrappedFileKey,
          content_nonce: uint8ArrayToHex(baseNonce),
        }),
      });

      uploadItem.status = "completed";
      uploadItem.progress = 100;
      await removeUploadState(initData.upload_session_id);

      // Refresh file list
      await filesStore.fetchNodes();
      // Update quota in authStore
      await authStore.fetchProfile();

      // Automatically remove completed item after 2 seconds so dialog closes automatically
      setTimeout(() => {
        const idx = uploads.value.findIndex((u) => u.id === uploadItem.id);
        if (idx !== -1 && uploads.value[idx].status === "completed") {
          uploads.value.splice(idx, 1);
        }
      }, 2000);
    } catch (err: any) {
      uploadItem.status = "error";
      uploadItem.errorMessage = err.message || "Upload failed";
    }
  }

  function pauseUpload(id: string) {
    const item = uploads.value.find((u) => u.id === id);
    if (item && item.status === "uploading") {
      item.status = "paused";
    }
  }

  function cancelUpload(id: string) {
    const itemIdx = uploads.value.findIndex((u) => u.id === id);
    if (itemIdx !== -1) {
      const item = uploads.value[itemIdx];
      if (item.uploadSessionId) {
        apiRequest(`/api/v1/uploads/${item.uploadSessionId}`, { method: "DELETE" }).catch(() => {});
        removeUploadState(item.uploadSessionId).catch(() => {});
      }
      uploads.value.splice(itemIdx, 1);
    }
  }

  function clearCompleted() {
    uploads.value = uploads.value.filter((u) => u.status !== "completed");
  }

  function toggleTray() {
    isTrayOpen.value = !isTrayOpen.value;
  }

  return {
    uploads,
    isTrayOpen,
    activeCount,
    totalProgress,
    uploadFile,
    pauseUpload,
    cancelUpload,
    clearCompleted,
    toggleTray,
  };
});
