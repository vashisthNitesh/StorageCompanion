import { defineStore } from "pinia";
import { ref, computed, reactive } from "vue";
import { ApiError, apiRequest, getAccessToken, refreshAccessToken } from "../lib/api";
import { normalizeApiError } from "../lib/errors";
import { emitAppEvent } from "../lib/events";
import { toast } from "../lib/toast";
import { useAuthStore } from "./auth";
import { useFilesStore, type FileNode } from "./files";
import { generateFileKey, generateRandomBytes, wrapKey } from "../lib/crypto/keys";
import { encryptName } from "../lib/crypto/names";
import { importFileKey, encryptChunkWithKey } from "../lib/crypto/content";
import { uint8ArrayToHex } from "../lib/crypto/kdf";

const MAX_PARALLEL_FILES = 2;
const PARTS_PER_FILE = 3;
const MAX_PART_ATTEMPTS = 6;

export type UploadStatus = "queued" | "encrypting" | "uploading" | "completing" | "completed" | "error" | "paused" | "cancelled";

export const STAGE_LABEL: Record<UploadStatus, string> = {
  queued: "Waiting",
  encrypting: "Encrypting",
  uploading: "Uploading",
  completing: "Verifying",
  completed: "Done",
  error: "Failed",
  paused: "Paused",
  cancelled: "Cancelled",
};

export interface UploadBatch {
  id: string;
  /** Destination folder name for messages ("uploaded to Projects"). */
  targetName: string;
  targetId: string | null;
  notified: boolean;
}

export interface ActiveUpload {
  id: string;
  batchId: string;
  /** Top-level folder name when the file came from a folder upload. */
  group?: string;
  file: File;
  /** Name stored in the vault (may differ from the file name after "Keep both"). */
  name: string;
  size: number;
  progress: number; // 0..100
  speedMBs: number;
  etaSeconds: number | null;
  status: UploadStatus;
  errorMessage?: string;
  /** Network hiccup notice while still uploading ("Reconnecting…"). */
  notice?: string;
  parentId: string | null;
  /** Existing file this upload becomes a new version of, and its current name. */
  nodeId?: string;
  keepName?: string;
  session?: { id: string; partSize: number; totalParts: number };
  fileKey?: Uint8Array;
  baseNonce?: Uint8Array;
  wrappedFileKey?: string;
  doneParts: Set<number>;
}

export interface UploadRequest {
  file: File;
  parentId: string | null;
  name?: string;
  nodeId?: string;
  keepName?: string;
  group?: string;
}

interface PartResult {
  ok: boolean;
  status: number;
  data?: any;
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
      let data: any;
      try {
        data = JSON.parse(xhr.responseText);
      } catch {}
      resolve({ ok: xhr.status >= 200 && xhr.status < 300, status: xhr.status, data });
    };
    xhr.onerror = () => resolve({ ok: false, status: 0 });
    xhr.ontimeout = () => resolve({ ok: false, status: 408 });
    xhr.onabort = () => resolve({ ok: false, status: -1 });
    xhr.send(body);
  });
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const waitForOnline = () =>
  new Promise<void>((resolve) => {
    if (navigator.onLine) return resolve();
    window.addEventListener("online", () => resolve(), { once: true });
  });

/** Turns a failed upload into one readable line, and opens the plan picker when that's the fix. */
function describeFailure(err: unknown): string {
  const n = normalizeApiError(err);
  if (n.kind === "plan_required" || n.kind === "quota") emitAppEvent("plan-picker", { reason: n.message });
  if (n.kind === "network") return "Connection lost. Retry when you're back online.";
  return n.message;
}

export const useUploadStore = defineStore("upload", () => {
  const authStore = useAuthStore();
  const filesStore = useFilesStore();
  const uploads = ref<ActiveUpload[]>([]);
  const batches = ref<UploadBatch[]>([]);
  const isTrayOpen = ref(false);
  /** Rendered height of the upload panel, so toasts can sit above it. */
  const panelHeight = ref(0);
  const aborters = new Map<string, { aborted: boolean; xhr?: XMLHttpRequest }[]>();

  const active = computed(() => uploads.value.filter((u) => ["queued", "encrypting", "uploading", "completing"].includes(u.status)));
  const activeCount = computed(() => active.value.length);
  const totalProgress = computed(() => {
    const list = uploads.value.filter((u) => u.status !== "cancelled");
    if (!list.length) return 100;
    const total = list.reduce((acc, u) => acc + u.size, 0) || 1;
    const done = list.reduce((acc, u) => acc + (u.size * (u.status === "completed" ? 100 : u.progress)) / 100, 0);
    return Math.min(100, Math.round((done / total) * 100));
  });
  const totalEta = computed(() => {
    const speed = active.value.reduce((s, u) => s + (u.speedMBs || 0), 0);
    if (!speed) return null;
    const remaining = active.value.reduce((s, u) => s + u.size * (1 - u.progress / 100), 0);
    return Math.round(remaining / 1048576 / speed);
  });

  function running() {
    return uploads.value.filter((u) => ["encrypting", "uploading", "completing"].includes(u.status)).length;
  }

  function pump() {
    while (running() < MAX_PARALLEL_FILES) {
      const next = uploads.value.find((u) => u.status === "queued");
      if (!next) break;
      void execute(next);
    }
    notifyFinishedBatches();
  }

  /** One toast per finished batch: "12 files uploaded to Projects" (with View), or a failure summary. */
  function notifyFinishedBatches() {
    for (const batch of batches.value) {
      if (batch.notified) continue;
      const items = uploads.value.filter((u) => u.batchId === batch.id);
      if (!items.length || items.some((u) => ["queued", "encrypting", "uploading", "completing", "paused"].includes(u.status))) continue;
      batch.notified = true;
      const done = items.filter((u) => u.status === "completed");
      const failed = items.filter((u) => u.status === "error");
      if (failed.length) {
        toast.error(`${failed.length} of ${items.length} ${items.length === 1 ? "upload" : "uploads"} failed.`, {
          action: { label: "Show", onClick: () => (isTrayOpen.value = true) },
        });
      } else if (done.length) {
        const what = done.length === 1 ? `“${done[0].name}”` : `${done.length} files`;
        const ids = done.map((u) => u.nodeId).filter(Boolean) as string[];
        toast.success(`${what} uploaded to ${batch.targetName}`, {
          action: {
            label: "View",
            onClick: async () => {
              const { router } = await import("../router");
              await router.push("/app/files");
              await filesStore.openFolderFromSearch(batch.targetId);
              filesStore.highlight(ids);
            },
          },
        });
      }
    }
  }

  async function startSession(item: ActiveUpload) {
    if (!authStore.masterKey) throw new Error("vault_locked");
    item.status = "encrypting";
    item.fileKey = generateFileKey();
    item.baseNonce = generateRandomBytes(12);
    item.wrappedFileKey = await wrapKey(authStore.masterKey, item.fileKey);
    const { ciphertextBase64, nonceHex } = await encryptName(authStore.masterKey, item.name);
    const init = await apiRequest<{ upload_session_id: string; part_size: number; total_parts: number }>("/api/v1/uploads", {
      method: "POST",
      body: JSON.stringify({
        parent_id: item.parentId,
        node_id: item.nodeId,
        encrypted_name: ciphertextBase64,
        name_nonce: nonceHex,
        size_bytes: item.file.size,
      }),
    });
    item.session = { id: init.upload_session_id, partSize: init.part_size, totalParts: init.total_parts };
    item.doneParts = new Set();
  }

  async function execute(item: ActiveUpload) {
    if (item.file.size <= 0) {
      item.status = "error";
      item.errorMessage = "This file is empty (0 bytes). If it's still downloading, wait for it to finish.";
      pump();
      return;
    }
    const controllers: { aborted: boolean; xhr?: XMLHttpRequest }[] = [];
    aborters.set(item.id, controllers);
    const isUploading = () => item.status === "uploading";

    try {
      if (!item.session || !item.fileKey || !item.baseNonce) await startSession(item);
      const { id: sessionId, partSize, totalParts } = item.session!;
      const cryptoKey = await importFileKey(item.fileKey!);
      item.status = "uploading";
      item.errorMessage = undefined;

      const inFlight = new Map<number, number>();
      let committed = 0;
      for (const n of item.doneParts) committed += Math.min(partSize, item.file.size - (n - 1) * partSize);
      const samples: { t: number; bytes: number }[] = [];

      const updateProgress = () => {
        let flying = 0;
        for (const v of inFlight.values()) flying += v;
        const bytes = Math.min(item.file.size, committed + flying);
        item.progress = Math.min(99, Math.round((bytes / item.file.size) * 100));
        const now = Date.now();
        samples.push({ t: now, bytes });
        while (samples.length > 2 && now - samples[0].t > 5000) samples.shift();
        const dt = (now - samples[0].t) / 1000;
        if (dt > 0.5) {
          item.speedMBs = Math.max(0, (bytes - samples[0].bytes) / 1048576 / dt);
          item.etaSeconds = item.speedMBs > 0.01 ? Math.round((item.file.size - bytes) / 1048576 / item.speedMBs) : null;
        }
      };

      const queue = Array.from({ length: totalParts }, (_, i) => i + 1).filter((n) => !item.doneParts.has(n));

      const worker = async () => {
        while (queue.length) {
          if (!isUploading()) return;
          const partNumber = queue.shift()!;
          const start = (partNumber - 1) * partSize;
          const plain = new Uint8Array(await item.file.slice(start, Math.min(item.file.size, start + partSize)).arrayBuffer());
          const encrypted = await encryptChunkWithKey(cryptoKey, plain, item.baseNonce!, partNumber);

          let attempt = 1;
          for (;;) {
            if (!isUploading()) return;
            if (!navigator.onLine) {
              // Waiting for the network doesn't use up retry attempts.
              item.notice = "Waiting for connection…";
              await waitForOnline();
              item.notice = undefined;
            }
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
              if (!(await refreshAccessToken())) throw new ApiError("auth", 401, {}, "http", "/api/v1/uploads");
              continue;
            }
            if ([400, 402, 403, 404, 413].includes(res.status)) throw new ApiError("upload", res.status, res.data ?? {}, "http", "/api/v1/uploads");
            if (res.status === 0 && !navigator.onLine) continue;
            attempt += 1;
            if (attempt > MAX_PART_ATTEMPTS) throw new ApiError("upload", res.status, res.data ?? {}, res.status === 0 ? "network" : "http", "/api/v1/uploads");
            item.notice = "Reconnecting…";
            await sleep(Math.min(15_000, 1000 * 2 ** (attempt - 2)));
            item.notice = undefined;
          }

          item.doneParts.add(partNumber);
          committed += plain.length;
          updateProgress();
        }
      };

      await Promise.all(Array.from({ length: Math.min(PARTS_PER_FILE, totalParts) }, worker));
      if (!isUploading()) return;

      item.status = "completing";
      item.etaSeconds = null;
      // Completing is idempotent on the server, so transient failures are retried.
      let node: (FileNode & { quota?: any }) | undefined;
      for (let attempt = 1; ; attempt++) {
        try {
          node = await apiRequest(`/api/v1/uploads/${sessionId}/complete`, {
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
      if (node) {
        const { quota, ...rest } = node;
        if (quota && authStore.user) authStore.user.quota = quota;
        item.nodeId = rest.id;
        filesStore.upsertUploaded({ ...rest, name: item.keepName ?? item.name });
      }
      setTimeout(() => {
        uploads.value = uploads.value.filter((u) => u.id !== item.id);
        if (!uploads.value.length) isTrayOpen.value = false;
      }, 8000);
    } catch (err) {
      if (item.status !== "paused" && item.status !== "cancelled") {
        item.status = "error";
        item.notice = undefined;
        item.errorMessage = err instanceof Error && err.message === "vault_locked" ? "Unlock your files, then retry." : describeFailure(err);
      }
    } finally {
      aborters.delete(item.id);
      pump();
    }
  }

  /** Queues a batch of already-checked uploads (see useUploader for pre-flight checks). */
  function enqueueBatch(requests: UploadRequest[], target: { id: string | null; name: string }) {
    if (!requests.length) return;
    const batch: UploadBatch = { id: crypto.randomUUID(), targetName: target.name, targetId: target.id, notified: false };
    batches.value = [...batches.value.filter((b) => !b.notified || uploads.value.some((u) => u.batchId === b.id)), batch];
    for (const r of requests) {
      uploads.value.push(
        reactive<ActiveUpload>({
          id: crypto.randomUUID(),
          batchId: batch.id,
          group: r.group,
          file: r.file,
          name: r.name ?? r.file.name,
          size: r.file.size,
          progress: 0,
          speedMBs: 0,
          etaSeconds: null,
          status: "queued",
          parentId: r.parentId,
          nodeId: r.nodeId,
          keepName: r.keepName,
          doneParts: new Set(),
        })
      );
    }
    isTrayOpen.value = true;
    pump();
  }

  /** Uploads `file` as a new version of an existing file. */
  function uploadNewVersion(file: File, node: { id: string; parent: string | null; name: string }) {
    enqueueBatch([{ file, parentId: node.parent, nodeId: node.id, keepName: node.name, name: node.name }], {
      id: node.parent,
      name: filesStore.breadcrumbs.at(-1)?.name ?? "My files",
    });
  }

  function retryUpload(id: string) {
    const item = uploads.value.find((u) => u.id === id);
    if (!item || (item.status !== "error" && item.status !== "paused")) return;
    const batch = batches.value.find((b) => b.id === item.batchId);
    if (batch) batch.notified = false;
    item.status = "queued";
    item.errorMessage = undefined;
    pump();
  }

  function retryFailed() {
    uploads.value.filter((u) => u.status === "error").forEach((u) => retryUpload(u.id));
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
      item.etaSeconds = null;
      stopTransfers(id);
      pump();
    }
  }

  function cancelUpload(id: string) {
    const item = uploads.value.find((u) => u.id === id);
    if (!item || item.status === "completed") return;
    item.status = "cancelled";
    stopTransfers(id);
    if (item.session) apiRequest(`/api/v1/uploads/${item.session.id}`, { method: "DELETE" }).catch(() => {});
    uploads.value = uploads.value.filter((u) => u.id !== id);
    pump();
  }

  function cancelAll() {
    for (const u of [...uploads.value]) if (u.status !== "completed") cancelUpload(u.id);
  }

  function clearFinished() {
    uploads.value = uploads.value.filter((u) => !["completed", "error", "cancelled"].includes(u.status));
    if (!uploads.value.length) isTrayOpen.value = false;
  }

  function showPanel() {
    isTrayOpen.value = true;
  }

  // Closing the tab would abort uploads; this is the one place a native prompt is allowed.
  if (typeof window !== "undefined") {
    window.addEventListener("beforeunload", (e) => {
      if (activeCount.value > 0) {
        e.preventDefault();
        e.returnValue = "";
      }
    });
  }

  return {
    uploads,
    batches,
    isTrayOpen,
    panelHeight,
    activeCount,
    totalProgress,
    totalEta,
    enqueueBatch,
    uploadNewVersion,
    retryUpload,
    retryFailed,
    pauseUpload,
    cancelUpload,
    cancelAll,
    clearFinished,
    showPanel,
  };
});
