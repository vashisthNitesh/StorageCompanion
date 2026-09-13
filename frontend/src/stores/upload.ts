import { defineStore } from "pinia";
import { ref, computed, reactive } from "vue";
import { apiRequest, getAccessToken } from "../lib/api";
import { useAuthStore } from "./auth";
import { useFilesStore } from "./files";
import { generateFileKey, generateRandomBytes, wrapKey } from "../lib/crypto/keys";
import { encryptName } from "../lib/crypto/names";
import {
  deriveChunkNonce,
  encryptChunk,
  importFileKey,
  encryptChunkWithKey,
} from "../lib/crypto/content";
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
  timeoutMs: number = 90000
): Promise<{ ok: boolean; status: number; etag: string; responseJson?: any }> {
  return new Promise((resolve) => {
    const xhr = new XMLHttpRequest();
    xhr.open(method, url, true);
    xhr.timeout = timeoutMs;
    for (const [k, v] of Object.entries(headers)) {
      xhr.setRequestHeader(k, v);
    }
    // Only send credentials (cookies) to same-origin backend endpoints, NEVER to Cloudflare R2 / S3 presigned URLs!
    const isSameOrigin =
      url.startsWith("/") ||
      (typeof window !== "undefined" && url.startsWith(window.location.origin));
    xhr.withCredentials = isSameOrigin;

    // Reset stall timer on progress to allow large chunks on slower connections
    let stallTimer: any = null;
    function resetStallTimer() {
      if (stallTimer) clearTimeout(stallTimer);
      stallTimer = setTimeout(() => {
        xhr.abort();
        resolve({ ok: false, status: 408, etag: "" });
      }, 30000); // 30 seconds of zero data progress before considering stalled
    }
    resetStallTimer();

    xhr.upload.onprogress = (e) => {
      resetStallTimer();
      if (e.lengthComputable) {
        onProgress(e.loaded, e.total);
      }
    };

    xhr.onload = () => {
      if (stallTimer) clearTimeout(stallTimer);
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

    xhr.onerror = () => {
      if (stallTimer) clearTimeout(stallTimer);
      resolve({ ok: false, status: 0, etag: "" });
    };
    xhr.ontimeout = () => {
      if (stallTimer) clearTimeout(stallTimer);
      resolve({ ok: false, status: 408, etag: "" });
    };
    xhr.onabort = () => {
      if (stallTimer) clearTimeout(stallTimer);
      resolve({ ok: false, status: 0, etag: "" });
    };

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
  initData?: any;
  fileKey?: Uint8Array;
  baseNonce?: Uint8Array;
  wrappedFileKey?: string;
  completedParts?: { part_number: number; etag: string }[];
  parentId?: string | null;
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

  async function executeUpload(uploadItem: ActiveUpload) {
    if (!authStore.masterKey) throw new Error("Vault must be unlocked to upload.");
    const file = uploadItem.file;

    try {
      let initData = uploadItem.initData;
      let fileKey = uploadItem.fileKey;
      let baseNonce = uploadItem.baseNonce;
      let wrappedFileKey = uploadItem.wrappedFileKey;

      if (!initData || !fileKey || !baseNonce || !wrappedFileKey) {
        uploadItem.status = "encrypting";

        // 1. Generate per-file AES-256-GCM key and 12-byte base nonce
        fileKey = generateFileKey();
        baseNonce = generateRandomBytes(12);

        // 2. Wrap File Key with user's Master Key
        wrappedFileKey = await wrapKey(authStore.masterKey, fileKey);

        // 3. Encrypt filename with Master Key
        const { ciphertextBase64, nonceHex } = await encryptName(
          authStore.masterKey,
          file.name
        );

        // 4. Request multipart upload from backend
        initData = await apiRequest<{
          upload_session_id: string;
          s3_upload_id: string;
          object_key: string;
          part_size: number;
          total_parts: number;
          presigned_urls: { part_number: number; url: string }[];
        }>("/api/v1/uploads", {
          method: "POST",
          body: JSON.stringify({
            parent_id: uploadItem.parentId || null,
            encrypted_name: ciphertextBase64,
            name_nonce: nonceHex,
            size_bytes: file.size,
          }),
        });

        uploadItem.initData = initData;
        uploadItem.fileKey = fileKey;
        uploadItem.baseNonce = baseNonce;
        uploadItem.wrappedFileKey = wrappedFileKey;
        uploadItem.uploadSessionId = initData.upload_session_id;
        uploadItem.completedParts = [];

        // Save initial state to IndexedDB for resumability
        const storedUpload: StoredUpload = {
          uploadSessionId: initData.upload_session_id,
          s3UploadId: initData.s3_upload_id,
          fileKeyHex: uint8ArrayToHex(fileKey),
          baseNonceHex: uint8ArrayToHex(baseNonce),
          wrappedFileKey,
          fileName: file.name,
          fileSize: file.size,
          partSize: initData.part_size,
          totalParts: initData.total_parts,
          completedParts: [],
          status: "uploading",
        };
        await saveUploadState(storedUpload).catch(() => {});
      }

      uploadItem.status = "uploading";
      uploadItem.errorMessage = undefined;

      const partSize = initData.part_size;
      const totalParts = initData.total_parts;
      const completedParts = uploadItem.completedParts || [];
      const alreadyCompleted = new Set(completedParts.map((p) => p.part_number));

      // Calculate initial committed bytes from already completed chunks
      let totalCommittedBytes = 0;
      for (const p of completedParts) {
        const isLast = p.part_number === totalParts;
        const thisPartSize = isLast ? (file.size - (totalParts - 1) * partSize) : partSize;
        totalCommittedBytes += thisPartSize;
      }

      // Concurrency: 2 for large files (> 500MB) to prevent uplink queue buildup; 3 for > 100MB; 4 for smaller files
      const concurrency = file.size > 500 * 1024 * 1024 ? 2 : (file.size > 100 * 1024 * 1024 ? 3 : 4);
      let nextPartIndex = 0;
      const inFlightBytes = new Map<number, number>();
      const speedSamples: { time: number; bytes: number }[] = [];
      const startTime = Date.now();

      // Pre-import CryptoKey once for the entire file to avoid repeated WebCrypto imports per chunk
      const importedCryptoKey = await importFileKey(fileKey);

      function updateProgress() {
        let activeInFlight = 0;
        for (const bytes of inFlightBytes.values()) {
          activeInFlight += bytes;
        }
        const currentBytes = Math.min(file.size, totalCommittedBytes + activeInFlight);
        uploadItem.completedBytes = currentBytes;
        uploadItem.progress = Math.min(99, Math.round((currentBytes / file.size) * 100));

        // Rolling speed calculation over the last 1.5-second sliding window
        const now = Date.now();
        speedSamples.push({ time: now, bytes: currentBytes });
        while (speedSamples.length > 1 && now - speedSamples[0].time > 1500) {
          speedSamples.shift();
        }

        if (speedSamples.length > 1) {
          const dt = (now - speedSamples[0].time) / 1000;
          const db = currentBytes - speedSamples[0].bytes;
          if (dt >= 0.2) {
            const rawSpeed = Number((db / (1024 * 1024) / dt).toFixed(1));
            uploadItem.speedMBs = Math.max(0.1, rawSpeed);
          }
        } else {
          const elapsedSec = (now - startTime) / 1000;
          if (elapsedSec > 0.2) {
            uploadItem.speedMBs = Number((currentBytes / (1024 * 1024) / elapsedSec).toFixed(1));
          }
        }
      }

      updateProgress();

      async function uploadNextPart(): Promise<void> {
        while (nextPartIndex < totalParts) {
          if ((uploadItem.status as string) === "paused") return;

          const partIndex = nextPartIndex++;
          const partNumber = partIndex + 1;

          // Skip if already successfully uploaded in a prior attempt
          if (alreadyCompleted.has(partNumber)) {
            continue;
          }

          const start = partIndex * partSize;
          const end = Math.min(file.size, start + partSize);
          const chunkBlob = file.slice(start, end);
          const chunkBuffer = await chunkBlob.arrayBuffer();
          const chunkBytes = new Uint8Array(chunkBuffer);

          // Encrypt chunk using AES-256-GCM with deterministic nonce: baseNonce ^ partNumber
          const encryptedChunk = await encryptChunkWithKey(
            importedCryptoKey,
            chunkBytes,
            baseNonce!,
            partNumber
          );

          // Find presigned URL if available
          const presignedUrl = initData.presigned_urls
            ? initData.presigned_urls.find((p: { part_number: number; url: string }) => p.part_number === partNumber)?.url
            : null;

          let retries = 5;
          let etag = "";
          let uploaded = false;
          let attempt = 0;

          while (retries > 0 && !uploaded) {
            attempt++;
            if ((uploadItem.status as string) === "paused") return;

            // 1. Try direct presigned upload to R2/S3 (fastest, zero server load)
            if (presignedUrl) {
              const directRes = await uploadPartWithProgress(
                presignedUrl,
                encryptedChunk,
                "PUT",
                { "Content-Type": "application/octet-stream" },
                (loaded) => {
                  inFlightBytes.set(partNumber, Math.min(chunkBytes.length, Math.round(loaded * (chunkBytes.length / encryptedChunk.length))));
                  updateProgress();
                },
                120000 // 120s timeout with stall detector
              );

              if (directRes.ok) {
                etag = directRes.etag || `"${partNumber}"`;
                uploaded = true;
                break;
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
              120000
            );

            if (relayRes.ok) {
              etag = relayRes.etag || relayRes.responseJson?.etag || `"${partNumber}"`;
              uploaded = true;
              break;
            } else {
              retries--;
              if (retries === 0) {
                throw new Error(`Failed to upload part ${partNumber}. Check network and click Retry.`);
              }
              // Exponential backoff
              const backoff = Math.min(10000, 1000 * Math.pow(1.8, attempt - 1));
              await new Promise((r) => setTimeout(r, backoff));
            }
          }

          inFlightBytes.delete(partNumber);
          totalCommittedBytes += chunkBytes.length;
          updateProgress();
          completedParts.push({ part_number: partNumber, etag });
          uploadItem.completedParts = completedParts;
          alreadyCompleted.add(partNumber);

          // Persist progress to IndexedDB
          const storedUpload: StoredUpload = {
            uploadSessionId: initData.upload_session_id,
            s3UploadId: initData.s3_upload_id,
            fileKeyHex: uint8ArrayToHex(fileKey!),
            baseNonceHex: uint8ArrayToHex(baseNonce!),
            wrappedFileKey: wrappedFileKey!,
            fileName: file.name,
            fileSize: file.size,
            partSize,
            totalParts,
            completedParts,
            status: "uploading",
          };
          await saveUploadState(storedUpload).catch(() => {});
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
      await removeUploadState(initData.upload_session_id).catch(() => {});

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
      console.error("Upload error:", err);
    }
  }

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
      parentId,
    });

    uploads.value.unshift(uploadItem);
    isTrayOpen.value = true;

    await executeUpload(uploadItem);
  }

  async function retryUpload(id: string) {
    const item = uploads.value.find((u) => u.id === id);
    if (!item) return;
    item.status = "queued";
    item.errorMessage = undefined;
    await executeUpload(item);
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
    retryUpload,
    pauseUpload,
    cancelUpload,
    clearCompleted,
    toggleTray,
  };
});
