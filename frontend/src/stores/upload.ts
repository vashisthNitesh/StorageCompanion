import { defineStore } from "pinia";
import { ref, computed, reactive } from "vue";
import { apiRequest, getAccessToken, refreshAccessToken } from "../lib/api";
import { useAuthStore } from "./auth";
import { useFilesStore } from "./files";
import { generateFileKey, generateRandomBytes, wrapKey } from "../lib/crypto/keys";
import { encryptName } from "../lib/crypto/names";
import { importFileKey, encryptChunkWithKey } from "../lib/crypto/content";
import { uint8ArrayToHex } from "../lib/crypto/kdf";

const MAX_PARALLEL_FILES = 2;
const PARTS_PER_FILE = 3;
const MAX_PART_ATTEMPTS = 6;

type UploadStatus = "queued" | "encrypting" | "uploading" | "completing" | "completed" | "error" | "paused";

export interface ActiveUpload {
  id: string;
  file: File;
  name: string;
  size: number;
  progress: number; // 0..100
  speedMBs: number;
  status: UploadStatus;
  errorMessage?: string;
  parentId: string | null;
  // Existing file this upload becomes a new version of
  nodeId?: string;
  // Resumable state for this browser session
  session?: { id: string; partSize: number; totalParts: number };
  fileKey?: Uint8Array;
  baseNonce?: Uint8Array;
  wrappedFileKey?: string;
  doneParts: Set<number>;
}

interface PartResult {
  ok: boolean;
  status: number;
  message?: string;
}

function sendPart(
  url: string,
  body: Uint8Array,
  token: string | null,
  onProgress: (loaded: number) => void,
  abortSignal: { aborted: boolean; xhr?: XMLHttpRequest }
): Promise<PartResult> {
  return new Promise((resolve) => {
    const xhr = new XMLHttpRequest();
    abortSignal.xhr = xhr;
    xhr.open("POST", url, true);
    xhr.timeout = 180_000;
    xhr.setRequestHeader("Content-Type", "application/octet-stream");
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.withCredentials = true;
    xhr.upload.onprogress = (e) => onProgress(e.loaded);
    xhr.onload = () => {
      let message: string | undefined;
      try {
        const data = JSON.parse(xhr.responseText);
        message = data.error || data.message;
      } catch {
        // not JSON
      }
      resolve({ ok: xhr.status >= 200 && xhr.status < 300, status: xhr.status, message });
    };
    xhr.onerror = () => resolve({ ok: false, status: 0 });
    xhr.ontimeout = () => resolve({ ok: false, status: 408 });
    xhr.onabort = () => resolve({ ok: false, status: -1 });
    xhr.send(body);
  });
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export const useUploadStore = defineStore("upload", () => {
  const authStore = useAuthStore();
  const filesStore = useFilesStore();
  const uploads = ref<ActiveUpload[]>([]);
  const isTrayOpen = ref(false);
  const aborters = new Map<string, { aborted: boolean; xhr?: XMLHttpRequest }[]>();

  const activeCount = computed(
    () => uploads.value.filter((u) => ["queued", "encrypting", "uploading", "completing"].includes(u.status)).length
  );
  const totalProgress = computed(() => {
    const active = uploads.value.filter((u) => u.status !== "completed");
    if (!active.length) return 100;
    const total = active.reduce((acc, u) => acc + u.size, 0) || 1;
    const done = active.reduce((acc, u) => acc + (u.size * u.progress) / 100, 0);
    return Math.round((done / total) * 100);
  });

  function running() {
    return uploads.value.filter((u) => ["encrypting", "uploading", "completing"].includes(u.status)).length;
  }

  function pump() {
    while (running() < MAX_PARALLEL_FILES) {
      const next = [...uploads.value].reverse().find((u) => u.status === "queued");
      if (!next) return;
      void execute(next);
    }
  }

  async function startSession(item: ActiveUpload) {
    if (!authStore.masterKey) throw new Error("Unlock your vault to upload.");
    item.status = "encrypting";
    item.fileKey = generateFileKey();
    item.baseNonce = generateRandomBytes(12);
    item.wrappedFileKey = await wrapKey(authStore.masterKey, item.fileKey);
    const { ciphertextBase64, nonceHex } = await encryptName(authStore.masterKey, item.file.name);
    const init = await apiRequest<{ upload_session_id: string; part_size: number; total_parts: number }>(
      "/api/v1/uploads",
      {
        method: "POST",
        body: JSON.stringify({
          parent_id: item.parentId,
          node_id: item.nodeId,
          encrypted_name: ciphertextBase64,
          name_nonce: nonceHex,
          size_bytes: item.file.size,
        }),
      }
    );
    item.session = { id: init.upload_session_id, partSize: init.part_size, totalParts: init.total_parts };
    item.doneParts = new Set();
  }

  async function execute(item: ActiveUpload) {
    if (item.file.size <= 0) {
      item.status = "error";
      item.errorMessage = "This file is empty (0 bytes). If it is still downloading, wait for it to finish.";
      return;
    }
    const controllers: { aborted: boolean; xhr?: XMLHttpRequest }[] = [];
    aborters.set(item.id, controllers);

    try {
      if (!item.session || !item.fileKey || !item.baseNonce) await startSession(item);
      const { id: sessionId, partSize, totalParts } = item.session!;
      const cryptoKey = await importFileKey(item.fileKey!);
      item.status = "uploading";
      item.errorMessage = undefined;

      const inFlight = new Map<number, number>();
      let committed = 0;
      for (const n of item.doneParts) committed += Math.min(partSize, item.file.size - (n - 1) * partSize);
      const started = Date.now();
      const startBytes = committed;

      const updateProgress = () => {
        let flying = 0;
        for (const v of inFlight.values()) flying += v;
        const bytes = Math.min(item.file.size, committed + flying);
        item.progress = Math.min(99, Math.round((bytes / item.file.size) * 100));
        const secs = (Date.now() - started) / 1000;
        if (secs > 0.5) item.speedMBs = Math.max(0, Number(((bytes - startBytes) / 1048576 / secs).toFixed(1)));
      };

      const queue = Array.from({ length: totalParts }, (_, i) => i + 1).filter((n) => !item.doneParts.has(n));

      const worker = async () => {
        while (queue.length) {
          if (item.status !== "uploading") return;
          const partNumber = queue.shift()!;
          const start = (partNumber - 1) * partSize;
          const plain = new Uint8Array(await item.file.slice(start, Math.min(item.file.size, start + partSize)).arrayBuffer());
          const encrypted = await encryptChunkWithKey(cryptoKey, plain, item.baseNonce!, partNumber);

          for (let attempt = 1; ; attempt++) {
            if (item.status !== "uploading") return;
            const signal: { aborted: boolean; xhr?: XMLHttpRequest } = { aborted: false };
            controllers.push(signal);
            const res = await sendPart(
              `/api/v1/uploads/${sessionId}/parts/${partNumber}`,
              encrypted,
              getAccessToken(),
              (loaded) => {
                inFlight.set(partNumber, Math.round((loaded / encrypted.length) * plain.length));
                updateProgress();
              },
              signal
            );
            inFlight.delete(partNumber);
            if (res.ok) break;
            if (res.status === -1) return; // paused or cancelled
            if (res.status === 401) {
              const refreshed = await refreshAccessToken();
              if (!refreshed) throw new Error("Your session expired. Sign in again to continue uploading.");
              continue;
            }
            if (res.status === 400 || res.status === 402 || res.status === 404 || res.status === 413) {
              throw new Error(res.message || "The server rejected this upload.");
            }
            if (attempt >= MAX_PART_ATTEMPTS) {
              throw new Error(res.message || "Upload keeps failing. Check your connection and press Retry.");
            }
            item.errorMessage = navigator.onLine ? `Retrying… (attempt ${attempt + 1})` : "You're offline. Waiting for connection…";
            await sleep(Math.min(15_000, 1000 * 2 ** (attempt - 1)));
            item.errorMessage = undefined;
          }

          item.doneParts.add(partNumber);
          committed += plain.length;
          updateProgress();
        }
      };

      await Promise.all(Array.from({ length: Math.min(PARTS_PER_FILE, totalParts) }, worker));
      if (item.status !== "uploading") return;

      item.status = "completing";
      // Completing is idempotent on the server, so transient failures are retried.
      let node: { quota?: any } | undefined;
      for (let attempt = 1; ; attempt++) {
        try {
          node = await apiRequest<{ quota?: any }>(`/api/v1/uploads/${sessionId}/complete`, {
            method: "POST",
            body: JSON.stringify({ wrapped_file_key: item.wrappedFileKey, content_nonce: uint8ArrayToHex(item.baseNonce!) }),
            timeoutMs: 120_000,
          });
          break;
        } catch (err: any) {
          const transient = !err?.status || err.status >= 500;
          if (!transient || attempt >= 4) throw err;
          await sleep(1500 * attempt);
        }
      }
      item.status = "completed";
      item.progress = 100;
      item.fileKey = undefined;
      if (node?.quota && authStore.user) authStore.user.quota = node.quota;
      filesStore.invalidateIndex();
      if (item.parentId === filesStore.currentParentId && !filesStore.isSearchActive) {
        void filesStore.fetchNodes(filesStore.currentParentId);
      }
      setTimeout(() => {
        uploads.value = uploads.value.filter((u) => u.id !== item.id || u.status !== "completed");
      }, 4000);
    } catch (err: any) {
      if (item.status !== "paused") {
        item.status = "error";
        item.errorMessage = err?.message || "Upload failed.";
      }
    } finally {
      aborters.delete(item.id);
      pump();
    }
  }

  function enqueue(file: File, parentId: string | null, nodeId?: string) {
    const item = reactive<ActiveUpload>({
      id: crypto.randomUUID(),
      file,
      name: file.name,
      size: file.size,
      progress: 0,
      speedMBs: 0,
      status: "queued",
      parentId,
      nodeId,
      doneParts: new Set(),
    });
    uploads.value.unshift(item);
    isTrayOpen.value = true;
  }

  /** Uploads files, recreating the folder structure of a dropped/selected directory. */
  async function uploadFiles(fileList: FileList | File[], rootParentId: string | null) {
    const files = Array.from(fileList as ArrayLike<File>);
    const folderIds = new Map<string, string | null>();

    async function ensureFolder(relDir: string): Promise<string | null> {
      if (!relDir) return rootParentId;
      if (folderIds.has(relDir)) return folderIds.get(relDir)!;
      const parts = relDir.split("/");
      const parent = await ensureFolder(parts.slice(0, -1).join("/"));
      const created = await filesStore.createFolder(parts[parts.length - 1], parent);
      folderIds.set(relDir, created.id);
      return created.id;
    }

    for (const file of files) {
      const rel = (file as File & { webkitRelativePath?: string }).webkitRelativePath || "";
      const dir = rel.includes("/") ? rel.split("/").slice(0, -1).join("/") : "";
      enqueue(file, await ensureFolder(dir));
    }
    pump();
  }

  /** Uploads `file` as a new version of an existing file. */
  function uploadNewVersion(file: File, node: { id: string; parent: string | null }) {
    enqueue(file, node.parent, node.id);
    pump();
  }

  function retryUpload(id: string) {
    const item = uploads.value.find((u) => u.id === id);
    if (!item || (item.status !== "error" && item.status !== "paused")) return;
    item.status = "queued";
    item.errorMessage = undefined;
    pump();
  }

  function stopTransfers(id: string) {
    for (const c of aborters.get(id) || []) {
      c.aborted = true;
      c.xhr?.abort();
    }
  }

  function pauseUpload(id: string) {
    const item = uploads.value.find((u) => u.id === id);
    if (item && (item.status === "uploading" || item.status === "queued")) {
      item.status = "paused";
      stopTransfers(id);
      pump();
    }
  }

  function cancelUpload(id: string) {
    const item = uploads.value.find((u) => u.id === id);
    if (!item) return;
    const wasActive = item.status !== "completed";
    item.status = "paused";
    stopTransfers(id);
    if (wasActive && item.session) {
      apiRequest(`/api/v1/uploads/${item.session.id}`, { method: "DELETE" }).catch(() => {});
    }
    uploads.value = uploads.value.filter((u) => u.id !== id);
    pump();
  }

  function cancelAll() {
    for (const u of [...uploads.value]) if (u.status !== "completed") cancelUpload(u.id);
  }

  function showPanel() {
    isTrayOpen.value = true;
  }

  function clearFinished() {
    uploads.value = uploads.value.filter((u) => u.status !== "completed" && u.status !== "error");
  }

  return {
    uploads,
    isTrayOpen,
    activeCount,
    totalProgress,
    uploadFiles,
    uploadNewVersion,
    retryUpload,
    pauseUpload,
    cancelUpload,
    clearFinished,
    showPanel,
    cancelAll,
  };
});
