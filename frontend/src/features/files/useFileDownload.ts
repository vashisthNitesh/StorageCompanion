import { ref } from "vue";
import { useAuthStore } from "../../stores/auth";
import { apiRequest, apiFetch } from "../../lib/api";
import { unwrapKey } from "../../lib/crypto/keys";
import { decryptFile } from "../../lib/crypto/content";
import { hexToUint8Array } from "../../lib/crypto/kdf";
import type { FileNode } from "../../stores/files";

const downloadingIds = ref<Set<string>>(new Set());

export function useFileDownload() {
  const authStore = useAuthStore();

  function isDownloading(nodeId: string): boolean {
    return downloadingIds.value.has(nodeId);
  }

  async function downloadFile(node: FileNode): Promise<void> {
    if (node.type === "folder") return;

    if (!authStore.masterKey) {
      alert("Please unlock your vault before downloading files.");
      return;
    }

    downloadingIds.value.add(node.id);

    try {
      // 1. Fetch download metadata (presigned/proxy URL & wrapped key)
      const downloadData = await apiRequest<{
        download_url: string;
        wrapped_file_key: string;
        content_nonce: string;
        size_bytes: number;
        part_size?: number;
        direct_url?: string;
      }>(`/api/v1/nodes/${node.id}/download`);

      // 2. Fetch encrypted bytes via authenticated content stream endpoint (with fallback)
      let res = await apiFetch(downloadData.download_url);
      if (!res.ok && downloadData.direct_url && downloadData.direct_url !== downloadData.download_url) {
        res = await apiFetch(downloadData.direct_url);
      }
      if (!res.ok) {
        throw new Error(`Failed to fetch file bytes from storage (${res.status})`);
      }

      const encryptedBuffer = await res.arrayBuffer();
      const encryptedBytes = new Uint8Array(encryptedBuffer);

      // 3. Unwrap File Key with user's Master Key
      const fileKey = await unwrapKey(authStore.masterKey, downloadData.wrapped_file_key);
      const baseNonce = hexToUint8Array(downloadData.content_nonce);

      // 4. Decrypt content client-side
      const partSize = downloadData.part_size || (8 * 1024 * 1024);
      const decryptedBytes = await decryptFile(fileKey, encryptedBytes, baseNonce, partSize);

      // 5. Trigger standard browser file download with decrypted blob
      const blob = new Blob([decryptedBytes], { type: "application/octet-stream" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = node.name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);

      setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch (err: any) {
      console.error("Download failed:", err);
      alert(err.message || "Failed to download and decrypt file.");
    } finally {
      downloadingIds.value.delete(node.id);
    }
  }

  return {
    downloadingIds,
    isDownloading,
    downloadFile,
  };
}
