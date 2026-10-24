import { ref } from "vue";
import { useAuthStore } from "../../stores/auth";
import { apiRequest, apiFetchRetrying, errorFromResponse } from "../../lib/api";
import { unwrapKey } from "../../lib/crypto/keys";
import { importFileKey, deriveChunkNonce } from "../../lib/crypto/content";
import { hexToUint8Array } from "../../lib/crypto/kdf";
import { normalizeApiError } from "../../lib/errors";
import { toast } from "../../lib/toast";
import type { FileNode } from "../../stores/files";

// Shared across components so every view shows the same progress.
const progress = ref<Record<string, number>>({});

interface DownloadInfo {
  download_url: string;
  wrapped_file_key: string;
  content_nonce: string;
  size_bytes: number;
  part_size: number;
}

const GCM_TAG = 16;
// Files at least this big are streamed straight to disk when the browser supports it.
const STREAM_TO_DISK_BYTES = 400 * 1024 * 1024;

class DecryptError extends Error {}

export function useFileDownload() {
  const authStore = useAuthStore();

  const keyFor = (node: FileNode, version?: number) => (version ? `${node.id}:v${version}` : node.id);
  const isDownloading = (node: FileNode, version?: number) => keyFor(node, version) in progress.value;
  const progressOf = (node: FileNode, version?: number) => progress.value[keyFor(node, version)] ?? 0;

  async function downloadFile(node: FileNode, version?: number): Promise<void> {
    if (node.type !== "file") return;
    if (!authStore.masterKey) {
      toast.info("Unlock your files first, then try the download again.");
      return;
    }
    const key = keyFor(node, version);
    if (key in progress.value) return;
    progress.value = { ...progress.value, [key]: 0 };
    const fileName = version ? `v${version} - ${node.name}` : node.name;
    let writable: any = null;

    try {
      const info = await apiRequest<DownloadInfo>(`/api/v1/nodes/${node.id}/download${version ? `?v=${version}` : ""}`);
      const total = info.size_bytes || node.size_bytes || 0;

      if (total >= STREAM_TO_DISK_BYTES && "showSaveFilePicker" in window) {
        try {
          const handle = await (window as any).showSaveFilePicker({ suggestedName: fileName });
          writable = await handle.createWritable();
        } catch (err: any) {
          if (err?.name === "AbortError") return;
          writable = null;
        }
      }

      const res = await apiFetchRetrying(info.download_url, { timeoutMs: 60_000 });
      if (!res.ok) throw await errorFromResponse(res);
      if (!res.body) throw new DecryptError();

      const fileKey = await importFileKey(await unwrapKey(authStore.masterKey, info.wrapped_file_key));
      const baseNonce = hexToUint8Array(info.content_nonce);
      const encPart = (info.part_size || 8 * 1024 * 1024) + GCM_TAG;
      const decryptPart = async (bytes: Uint8Array, n: number) => {
        try {
          return new Uint8Array(await crypto.subtle.decrypt({ name: "AES-GCM", iv: deriveChunkNonce(baseNonce, n) }, fileKey, bytes));
        } catch {
          throw new DecryptError();
        }
      };

      const reader = res.body.getReader();
      const parts: Uint8Array[] = [];
      let buffer = new Uint8Array(encPart * 2);
      let buffered = 0;
      let partNumber = 1;
      let received = 0;
      const emit = async (plain: Uint8Array) => (writable ? writable.write(plain) : parts.push(plain));

      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        if (!value?.length) continue;
        received += value.length;
        if (total) progress.value = { ...progress.value, [key]: Math.min(99, Math.round((received / (total + GCM_TAG)) * 100)) };
        if (buffered + value.length > buffer.length) {
          const grown = new Uint8Array(Math.max(buffer.length * 2, buffered + value.length));
          grown.set(buffer.subarray(0, buffered));
          buffer = grown;
        }
        buffer.set(value, buffered);
        buffered += value.length;
        while (buffered >= encPart) {
          await emit(await decryptPart(buffer.slice(0, encPart), partNumber++));
          buffer.copyWithin(0, encPart, buffered);
          buffered -= encPart;
        }
      }
      if (buffered > 0) await emit(await decryptPart(buffer.slice(0, buffered), partNumber));

      if (writable) {
        await writable.close();
        writable = null;
      } else {
        const url = URL.createObjectURL(new Blob(parts as BlobPart[], { type: "application/octet-stream" }));
        const a = document.createElement("a");
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 30_000);
      }
    } catch (err) {
      try {
        await writable?.abort();
      } catch {}
      const message =
        err instanceof DecryptError
          ? `“${node.name}” couldn't be decrypted. The file may be damaged.`
          : `Couldn't download “${node.name}”. ${normalizeApiError(err).message}`;
      toast.error(message, { retry: () => void downloadFile(node, version) });
    } finally {
      const next = { ...progress.value };
      delete next[key];
      progress.value = next;
    }
  }

  return { isDownloading, progressOf, downloadFile };
}
