import { ref } from "vue";
import { useAuthStore } from "../../stores/auth";
import { apiRequest } from "../../lib/api";
import { downloadDecryptRanged } from "../../lib/api/storageFetch";
import { unwrapKey } from "../../lib/crypto/keys";
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

    let writableStream: any = null;
    const knownSize = node.size_bytes || 0;
    const hasFsAccess = typeof window !== "undefined" && "showSaveFilePicker" in window;

    // In-memory assembly needs ~2x the file size in RAM; past this the tab would crash instead
    // of downloading. Say so up front.
    const MEMORY_LIMIT = 2 * 1024 * 1024 * 1024;
    if (!hasFsAccess && knownSize > MEMORY_LIMIT) {
      alert(
        "This file is too large to decrypt in this browser's memory. Please download it with Chrome or Edge on a desktop, which can stream it straight to disk."
      );
      return;
    }

    // The save picker must be opened while the click's user activation is still valid, i.e.
    // BEFORE any network await. Previously it ran after /download (which can take several
    // seconds), so Chrome rejected it, the code silently fell back to buffering the whole file
    // in memory, and nothing visible happened until the entire file was downloaded.
    if (hasFsAccess && knownSize >= 100 * 1024 * 1024) {
      try {
        const fileHandle = await (window as any).showSaveFilePicker({ suggestedName: node.name });
        writableStream = await fileHandle.createWritable();
      } catch (pickerErr: any) {
        if (pickerErr?.name === "AbortError") return; // user cancelled
        writableStream = null; // fall back to in-memory assembly
      }
    }

    downloadingIds.value.add(node.id);
    downloadProgress.value[node.id] = 0;
    downloadStatusText.value[node.id] = "Connecting...";

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

      const totalSize = downloadData.size_bytes || knownSize;

      downloadStatusText.value[node.id] = "Downloading...";

      // 2. Unwrap File Key with user's Master Key
      const fileKey = await unwrapKey(authStore.masterKey, downloadData.wrapped_file_key);
      const baseNonce = hexToUint8Array(downloadData.content_nonce);
      const partSize = downloadData.part_size || (8 * 1024 * 1024);
      const decryptedParts: Uint8Array[] = [];

      // 3. Ranged, resumable fetch + chunked AES-GCM decryption. Each decrypted part goes
      //    straight to disk (File System Access API) or into a Blob part list; a dropped
      //    connection resumes from the next undecrypted part instead of restarting 2.7 GB.
      await downloadDecryptRanged(downloadData, {
        fileKey,
        baseNonce,
        partSize,
        plainSize: totalSize,
        onPart: async (plain) => {
          if (writableStream) await writableStream.write(plain);
          else decryptedParts.push(plain);
        },
        onProgress: (done, total) => {
          const pct = Math.min(99, Math.round((done / Math.max(1, total)) * 100));
          downloadProgress.value[node.id] = pct;
          const mbDone = (done / (1024 * 1024)).toFixed(0);
          const mbTotal = (total / (1024 * 1024)).toFixed(0);
          downloadStatusText.value[node.id] = `${pct}% (${mbDone}/${mbTotal} MB)`;
        },
      });

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
      const raw = String(err?.message || "");
      // Never show an HTML error page or stack in the alert
      const msg = !raw || /<[a-z!]/i.test(raw) ? "Failed to download and decrypt file. Please try again." : raw;
      alert(`Download failed: ${msg}`);
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
