import { ref } from "vue";
import { useAuthStore } from "../../stores/auth";
import { apiRequest, apiFetch } from "../../lib/api";
import { unwrapKey } from "../../lib/crypto/keys";
import { decryptChunk } from "../../lib/crypto/content";
import { hexToUint8Array } from "../../lib/crypto/kdf";
import type { FileNode } from "../../stores/files";

const downloadingIds = ref<Set<string>>(new Set());
const downloadProgress = ref<Record<string, number>>({});
const downloadStatusText = ref<Record<string, string>>({});

export function useFileDownload() {
  const authStore = useAuthStore();

  function isDownloading(nodeId: string): boolean {
    return downloadingIds.value.has(nodeId);
  }

  function getProgress(nodeId: string): number {
    return downloadProgress.value[nodeId] || 0;
  }

  function getStatusText(nodeId: string): string {
    return downloadStatusText.value[nodeId] || "";
  }

  async function downloadFile(node: FileNode): Promise<void> {
    if (node.type === "folder") return;

    if (!authStore.masterKey) {
      alert("Please unlock your vault before downloading files.");
      return;
    }

    downloadingIds.value.add(node.id);
    downloadProgress.value[node.id] = 0;
    downloadStatusText.value[node.id] = "Connecting...";

    let writableStream: any = null;

    try {
      // 1. Fetch download metadata (presigned/proxy URL & wrapped key)
      const downloadData = await apiRequest<{
        download_url: string;
        wrapped_file_key: string;
        content_nonce: string;
        size_bytes: number;
        part_size?: number;
        direct_url?: string;
        upstream?: string;
      }>(`/api/v1/nodes/${node.id}/download`);

      const totalSize = downloadData.size_bytes || node.size_bytes || 0;
      const isLargeFile = totalSize >= 400 * 1024 * 1024; // >= 400 MB

      // For large files (> 400 MB), try File System Access API for zero-RAM direct-to-disk streaming
      if (isLargeFile && typeof window !== "undefined" && "showSaveFilePicker" in window) {
        try {
          downloadStatusText.value[node.id] = "Choose save location...";
          const fileHandle = await (window as any).showSaveFilePicker({
            suggestedName: node.name,
          });
          writableStream = await fileHandle.createWritable();
        } catch (pickerErr: any) {
          if (pickerErr.name === "AbortError") {
            // User cancelled the file picker dialog
            return;
          }
          // Fall back to in-memory chunked blob assembly
          writableStream = null;
        }
      }

      downloadStatusText.value[node.id] = "Downloading...";

      // 2. Fetch encrypted bytes: try direct storage edge download first, falling back to authenticated backend proxy
      let res: Response | null = null;
      if (downloadData.direct_url) {
        try {
          const directRes = await fetch(downloadData.direct_url, { method: "GET" });
          if (directRes.ok && directRes.body) {
            res = directRes;
          }
        } catch {
          // Direct edge download failed (e.g. CORS or network), fall back to backend proxy
          res = null;
        }
      }

      if (!res) {
        res = await apiFetch(downloadData.download_url);
      }

      if (!res.ok) {
        let errMessage = `Failed to fetch file from storage (${res.status})`;
        try {
          const errJson = await res.json();
          if (errJson.error) {
            errMessage = errJson.error;
          }
        } catch {}
        throw new Error(errMessage);
      }

      // 3. Unwrap File Key with user's Master Key
      const fileKey = await unwrapKey(authStore.masterKey, downloadData.wrapped_file_key);
      const baseNonce = hexToUint8Array(downloadData.content_nonce);
      const partSize = downloadData.part_size || (8 * 1024 * 1024);
      const encPartSize = partSize + 16;

      // 4. Stream and decrypt chunk-by-chunk without loading multi-gigabytes into a single ArrayBuffer
      if (!res.body) {
        throw new Error("Download stream response body is unavailable.");
      }

      const reader = res.body.getReader();
      const decryptedParts: Uint8Array[] = [];

      let accumulated = new Uint8Array(encPartSize * 2);
      let accumulatedLen = 0;
      let partNumber = 1;
      let receivedBytes = 0;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        if (value && value.length > 0) {
          receivedBytes += value.length;
          if (totalSize > 0) {
            const pct = Math.min(99, Math.round((receivedBytes / totalSize) * 100));
            downloadProgress.value[node.id] = pct;
            const mbTransferred = (receivedBytes / (1024 * 1024)).toFixed(0);
            const mbTotal = (totalSize / (1024 * 1024)).toFixed(0);
            downloadStatusText.value[node.id] = `${pct}% (${mbTransferred}/${mbTotal} MB)`;
          }

          // Expand buffer if needed
          if (accumulatedLen + value.length > accumulated.length) {
            const nextCapacity = Math.max(accumulated.length * 2, accumulatedLen + value.length + encPartSize);
            const newBuf = new Uint8Array(nextCapacity);
            newBuf.set(accumulated.subarray(0, accumulatedLen), 0);
            accumulated = newBuf;
          }
          accumulated.set(value, accumulatedLen);
          accumulatedLen += value.length;

          // Decrypt completed parts
          while (accumulatedLen >= encPartSize) {
            const encryptedChunk = accumulated.slice(0, encPartSize);
            const decryptedChunk = await decryptChunk(fileKey, encryptedChunk, baseNonce, partNumber);
            partNumber++;

            if (writableStream) {
              await writableStream.write(decryptedChunk);
            } else {
              decryptedParts.push(decryptedChunk);
            }

            // Shift remaining bytes to front
            const remaining = accumulatedLen - encPartSize;
            accumulated.copyWithin(0, encPartSize, accumulatedLen);
            accumulatedLen = remaining;
          }
        }
      }

      // Decrypt any final remaining chunk
      if (accumulatedLen > 0) {
        const finalChunk = accumulated.slice(0, accumulatedLen);
        const decryptedChunk = await decryptChunk(fileKey, finalChunk, baseNonce, partNumber);
        if (writableStream) {
          await writableStream.write(decryptedChunk);
        } else {
          decryptedParts.push(decryptedChunk);
        }
      }

      downloadProgress.value[node.id] = 100;
      downloadStatusText.value[node.id] = "Finishing...";

      // 5. Finalize file write or trigger standard browser download
      if (writableStream) {
        await writableStream.close();
        writableStream = null;
      } else {
        // Build Blob from chunk array (never requires a single 2GB contiguous ArrayBuffer in V8)
        const blob = new Blob(decryptedParts, { type: "application/octet-stream" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = node.name;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(url), 15000);
      }
    } catch (err: any) {
      if (writableStream) {
        try {
          await writableStream.abort();
        } catch {}
      }
      console.error("Download failed:", err);
      alert(err.message || "Failed to download and decrypt file.");
    } finally {
      downloadingIds.value.delete(node.id);
      delete downloadProgress.value[node.id];
      delete downloadStatusText.value[node.id];
    }
  }

  return {
    downloadingIds,
    downloadProgress,
    downloadStatusText,
    isDownloading,
    getProgress,
    getStatusText,
    downloadFile,
  };
}
