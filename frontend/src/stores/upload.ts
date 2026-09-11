import { defineStore } from "pinia";
import { ref, computed, reactive } from "vue";
import { apiRequest } from "../lib/api";
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
      let uploadedBytes = 0;
      const startTime = Date.now();

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
          const presignedUrl = initData.presigned_urls?.find(
            (p: { part_number: number; url: string }) => p.part_number === partNumber
          )?.url;

          // Upload chunk: try direct PUT first, fallback to backend relay if blocked (e.g. CORS/network policies)
          let retries = 3;
          let etag = "";
          let uploaded = false;

          while (retries > 0 && !uploaded) {
            if (presignedUrl) {
              try {
                const putRes = await fetch(presignedUrl, {
                  method: "PUT",
                  body: encryptedChunk,
                  headers: {
                    "Content-Type": "application/octet-stream",
                  },
                });

                if (putRes.ok) {
                  etag = putRes.headers.get("ETag") || `"${partNumber}"`;
                  uploaded = true;
                  break;
                }
              } catch {
                // Direct upload failed or blocked by CORS, fallback to proxy relay
              }
            }

            // Fallback: relay through backend API endpoint
            try {
              const relayRes = await apiRequest<{ status: string; etag: string; part_number: number }>(
                `/api/v1/uploads/${initData.upload_session_id}/parts/${partNumber}`,
                {
                  method: "POST",
                  body: encryptedChunk,
                  headers: {
                    "Content-Type": "application/octet-stream",
                  },
                }
              );
              etag = relayRes.etag || `"${partNumber}"`;
              uploaded = true;
              break;
            } catch (relayErr) {
              retries--;
              if (retries === 0) throw relayErr;
              await new Promise((r) => setTimeout(r, 1000));
            }
          }

          completedParts.push({ part_number: partNumber, etag });
          uploadedBytes += chunkBytes.length;
          uploadItem.completedBytes = uploadedBytes;
          uploadItem.progress = Math.min(99, Math.round((uploadedBytes / file.size) * 100));

          const elapsedSec = (Date.now() - startTime) / 1000;
          if (elapsedSec > 0) {
            uploadItem.speedMBs = Number((uploadedBytes / (1024 * 1024) / elapsedSec).toFixed(1));
          }

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
    toggleTray,
  };
});
