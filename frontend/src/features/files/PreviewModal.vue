<script setup lang="ts">
import { ref, watch } from "vue";
import { apiRequest } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import { decryptFile } from "../../lib/crypto/content";
import { unwrapKey } from "../../lib/crypto/keys";
import { hexToUint8Array } from "../../lib/crypto/kdf";
import {
  X,
  Download,
  AlertCircle,
  FileText,
  Loader2,
  FileVideo,
  FileAudio,
  FileSpreadsheet,
  FileCode,
  FileArchive,
  File as FileIcon,
  ExternalLink,
} from "lucide-vue-next";

const props = defineProps<{
  isOpen: boolean;
  node: any;
}>();

const emit = defineEmits(["close"]);

const authStore = useAuthStore();
const isLoading = ref(false);
const error = ref("");
const previewUrl = ref<string | null>(null);
const textContent = ref<string | null>(null);
const docHtml = ref<string | null>(null);
const decryptedData = ref<Uint8Array | null>(null);
const fileType = ref<"image" | "video" | "audio" | "text" | "pdf" | "docx" | "doc" | "unknown">("unknown");

watch(
  [() => props.node, () => props.isOpen],
  async ([newNode, isOpen]) => {
    if (newNode && isOpen) {
      await loadAndDecryptPreview(newNode);
    } else if (!isOpen) {
      cleanup();
    }
  },
  { immediate: true }
);

function cleanup() {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value);
    previewUrl.value = null;
  }
  textContent.value = null;
  docHtml.value = null;
  decryptedData.value = null;
  error.value = "";
}

function detectType(filename: string): "image" | "video" | "audio" | "text" | "pdf" | "docx" | "doc" | "unknown" {
  const ext = filename?.split(".").pop()?.toLowerCase() || "";
  if (["png", "jpg", "jpeg", "webp", "gif", "svg", "bmp", "ico", "avif"].includes(ext)) return "image";
  if (["mp4", "webm", "mov", "mkv", "avi", "m4v", "ogv", "3gp"].includes(ext)) return "video";
  if (["mp3", "wav", "ogg", "m4a", "flac", "aac"].includes(ext)) return "audio";
  if (["txt", "md", "markdown", "json", "js", "ts", "jsx", "tsx", "py", "html", "htm", "css", "scss", "vue", "rs", "go", "c", "cpp", "h", "java", "kt", "php", "rb", "sh", "bash", "zsh", "yaml", "yml", "toml", "ini", "conf", "env", "sql", "csv", "tsv", "log", "xml"].includes(ext)) return "text";
  if (ext === "pdf") return "pdf";
  if (ext === "docx") return "docx";
  if (["doc", "odt", "rtf", "xlsx", "xls", "pptx", "ppt"].includes(ext)) return "doc";
  return "unknown";
}

function formatBytes(bytes: number): string {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

async function loadAndDecryptPreview(node: any) {
  isLoading.value = true;
  error.value = "";
  cleanup();

  try {
    if (!authStore.masterKey) throw new Error("Vault is locked");

    // 1. Get presigned GET URL & wrapped key from backend
    const downloadData = await apiRequest<{
      download_url: string;
      wrapped_file_key: string;
      content_nonce: string;
      size_bytes: number;
      part_size?: number;
    }>(`/api/v1/nodes/${node.id}/download`);

    // 2. Fetch encrypted bytes (via authenticated content stream endpoint)
    const res = await fetch(downloadData.download_url);
    if (!res.ok) throw new Error(`Failed to fetch file bytes from storage (${res.status})`);
    const encryptedBuffer = await res.arrayBuffer();
    const encryptedBytes = new Uint8Array(encryptedBuffer);

    // 3. Unwrap File Key
    const fileKey = await unwrapKey(authStore.masterKey, downloadData.wrapped_file_key);
    const baseNonce = hexToUint8Array(downloadData.content_nonce);

    // 4. Decrypt content (supports single chunk and multi-chunk files of any size)
    const partSize = downloadData.part_size || (8 * 1024 * 1024);
    const decryptedBytes = await decryptFile(fileKey, encryptedBytes, baseNonce, partSize);
    decryptedData.value = decryptedBytes;

    const type = detectType(node.name);
    fileType.value = type;

    if (type === "text") {
      textContent.value = new TextDecoder().decode(decryptedBytes);
    } else if (type === "docx") {
      try {
        const mammoth = await import("mammoth");
        const result = await mammoth.convertToHtml({ arrayBuffer: decryptedBytes.buffer });
        docHtml.value = result.value || "<p class='text-slate-400 italic'>Document contains no text content.</p>";
      } catch (docErr: any) {
        docHtml.value = null;
      }
      const blob = new Blob([decryptedBytes], {
        type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      });
      previewUrl.value = URL.createObjectURL(blob);
    } else {
      const mimeMap: Record<string, string> = {
        image: "image/jpeg",
        video: "video/mp4",
        audio: "audio/mpeg",
        pdf: "application/pdf",
      };
      const ext = node.name?.split(".").pop()?.toLowerCase() || "";
      let mime = mimeMap[type] || "application/octet-stream";
      if (type === "video") {
        if (ext === "webm") mime = "video/webm";
        else if (ext === "mov") mime = "video/quicktime";
        else if (ext === "mkv") mime = "video/x-matroska";
      } else if (type === "image") {
        if (ext === "png") mime = "image/png";
        else if (ext === "webp") mime = "image/webp";
        else if (ext === "svg") mime = "image/svg+xml";
        else if (ext === "gif") mime = "image/gif";
      }
      const blob = new Blob([decryptedBytes], { type: mime });
      previewUrl.value = URL.createObjectURL(blob);
    }
  } catch (err: any) {
    error.value = err.message || "Failed to decrypt preview in browser.";
  } finally {
    isLoading.value = false;
  }
}

function handleDownload() {
  if (!props.node) return;
  let url = previewUrl.value;
  let shouldRevoke = false;

  if (!url && decryptedData.value) {
    const blob = new Blob([decryptedData.value], { type: "application/octet-stream" });
    url = URL.createObjectURL(blob);
    shouldRevoke = true;
  } else if (!url && textContent.value) {
    const blob = new Blob([textContent.value], { type: "text/plain;charset=utf-8" });
    url = URL.createObjectURL(blob);
    shouldRevoke = true;
  }

  if (url) {
    const a = document.createElement("a");
    a.href = url;
    a.download = props.node.name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    if (shouldRevoke) {
      setTimeout(() => URL.revokeObjectURL(url!), 1000);
    }
  }
}

function openInNewTab() {
  if (previewUrl.value) {
    window.open(previewUrl.value, "_blank");
  }
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
    <div class="w-full max-w-4xl max-h-[90vh] rounded-2xl overflow-hidden border border-slate-200 flex flex-col bg-white shadow-2xl">
      <!-- Header -->
      <div class="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between shrink-0">
        <div class="flex items-center space-x-3 truncate">
          <FileText class="w-5 h-5 text-blue-600 shrink-0" />
          <div class="min-w-0">
            <span class="font-bold text-slate-900 text-sm truncate block">{{ node?.name }}</span>
            <span class="text-[10px] text-slate-500 font-mono">{{ formatBytes(node?.size_bytes || 0) }} • End-to-End Encrypted</span>
          </div>
        </div>

        <div class="flex items-center space-x-2">
          <button
            v-if="previewUrl && (fileType === 'pdf' || fileType === 'image')"
            @click="openInNewTab"
            class="btn-secondary px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-700 flex items-center space-x-1.5 shadow-2xs"
            title="Open in new tab"
          >
            <ExternalLink class="w-3.5 h-3.5" />
            <span class="hidden sm:inline">New Tab</span>
          </button>
          <button
            v-if="previewUrl || textContent || docHtml || decryptedData"
            @click="handleDownload"
            class="btn-primary px-3.5 py-1.5 rounded-lg text-xs font-semibold text-white flex items-center space-x-1.5 shadow-xs"
          >
            <Download class="w-3.5 h-3.5" />
            <span>Save Decrypted</span>
          </button>
          <button @click="emit('close')" class="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors">
            <X class="w-5 h-5" />
          </button>
        </div>
      </div>

      <!-- Preview Body -->
      <div class="flex-1 overflow-auto p-6 flex items-center justify-center min-h-[350px] bg-[#F8FAFC]">
        <div v-if="isLoading" class="flex flex-col items-center space-y-3 text-slate-500 text-xs">
          <Loader2 class="w-8 h-8 text-blue-600 animate-spin" />
          <span class="font-medium">Streaming & Decrypting file client-side...</span>
          <span class="text-[11px] text-slate-400 font-mono">Zero-Knowledge AES-256-GCM</span>
        </div>

        <div v-else-if="error" class="flex flex-col items-center space-y-2 text-rose-600 text-xs text-center max-w-md p-6 bg-white rounded-2xl border border-rose-200 shadow-sm">
          <AlertCircle class="w-8 h-8 text-rose-500" />
          <span class="font-bold text-sm">Failed to Open File</span>
          <span class="text-slate-600 leading-relaxed">{{ error }}</span>
          <button
            v-if="node"
            @click="loadAndDecryptPreview(node)"
            class="btn-secondary px-3.5 py-1.5 rounded-lg text-xs font-medium text-slate-700 mt-2"
          >
            Retry Decryption
          </button>
        </div>

        <!-- Render Image -->
        <img
          v-else-if="fileType === 'image' && previewUrl"
          :src="previewUrl"
          :alt="node?.name"
          class="max-w-full max-h-[70vh] object-contain rounded-xl shadow-md border border-slate-200 bg-white"
        />

        <!-- Render Video -->
        <div v-else-if="fileType === 'video' && previewUrl" class="w-full flex justify-center">
          <video
            :src="previewUrl"
            controls
            playsinline
            class="max-w-full max-h-[70vh] rounded-xl shadow-md border border-slate-200 bg-black"
          ></video>
        </div>

        <!-- Render PDF in embedded viewer -->
        <iframe
          v-else-if="fileType === 'pdf' && previewUrl"
          :src="previewUrl"
          class="w-full h-[72vh] rounded-xl border border-slate-200 bg-white shadow-xs"
          title="PDF Document Viewer"
        ></iframe>

        <!-- Render Word Document (DOCX) converted to HTML -->
        <div
          v-else-if="fileType === 'docx' && docHtml"
          class="w-full max-h-[72vh] overflow-y-auto bg-white p-8 rounded-xl border border-slate-200 shadow-sm text-slate-800 leading-relaxed space-y-4"
        >
          <div class="border-b border-slate-100 pb-3 mb-4 flex items-center justify-between">
            <span class="text-xs font-semibold text-blue-600 uppercase tracking-wider">Word Document Preview</span>
            <span class="text-[11px] text-slate-400">{{ node?.name }}</span>
          </div>
          <div class="prose max-w-none text-xs leading-relaxed" v-html="docHtml"></div>
        </div>

        <!-- Render Audio -->
        <div v-else-if="fileType === 'audio' && previewUrl" class="p-8 rounded-2xl bg-white border border-slate-200 shadow-md text-center space-y-4 max-w-md w-full">
          <FileAudio class="w-12 h-12 text-blue-600 mx-auto" />
          <div>
            <div class="text-sm font-bold text-slate-900 truncate">{{ node?.name }}</div>
            <div class="text-xs text-slate-500 font-mono mt-0.5">{{ formatBytes(node?.size_bytes || 0) }}</div>
          </div>
          <audio :src="previewUrl" controls class="w-full pt-2"></audio>
        </div>

        <!-- Render Text / Code -->
        <pre
          v-else-if="fileType === 'text' && textContent"
          class="w-full p-5 rounded-xl bg-white border border-slate-200 font-mono text-xs text-slate-800 overflow-x-auto max-h-[68vh] leading-relaxed shadow-xs select-text"
        ><code>{{ textContent }}</code></pre>

        <!-- Document / Office Card Fallback (DOC, XLS, PPT, Archives) -->
        <div v-else class="p-8 rounded-2xl bg-white border border-slate-200 shadow-md text-center space-y-4 max-w-md w-full">
          <div class="w-14 h-14 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center mx-auto text-blue-600">
            <FileSpreadsheet v-if="['xlsx', 'xls', 'csv'].includes(node?.name?.split('.').pop()?.toLowerCase())" class="w-7 h-7" />
            <FileText v-else-if="['doc', 'odt', 'rtf'].includes(node?.name?.split('.').pop()?.toLowerCase())" class="w-7 h-7" />
            <FileIcon v-else class="w-7 h-7" />
          </div>

          <div>
            <h4 class="text-sm font-bold text-slate-900 truncate" :title="node?.name">{{ node?.name }}</h4>
            <p class="text-xs text-slate-500 mt-1">
              {{ formatBytes(node?.size_bytes || 0) }} • Decrypted in memory
            </p>
            <p class="text-[11px] text-slate-400 mt-0.5">
              In-browser interactive render not supported for this binary format. You can download the decrypted file.
            </p>
          </div>

          <div class="pt-2 flex justify-center space-x-2">
            <button
              @click="handleDownload"
              class="btn-primary px-4 py-2 rounded-xl text-white font-semibold text-xs shadow-xs flex items-center space-x-1.5"
            >
              <Download class="w-4 h-4" />
              <span>Download Decrypted File</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
