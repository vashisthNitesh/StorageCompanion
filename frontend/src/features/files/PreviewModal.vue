<script setup lang="ts">
import { ref, watch } from "vue";
import { apiRequest } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import { decryptChunk } from "../../lib/crypto/content";
import { unwrapKey } from "../../lib/crypto/keys";
import { hexToUint8Array } from "../../lib/crypto/kdf";
import { X, Download, AlertCircle, FileText, Loader2 } from "lucide-vue-next";

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
const fileType = ref<"image" | "video" | "audio" | "text" | "pdf" | "unknown">("unknown");

watch(
  () => props.node,
  async (newNode) => {
    if (newNode && props.isOpen) {
      await loadAndDecryptPreview(newNode);
    } else {
      cleanup();
    }
  }
);

function cleanup() {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value);
    previewUrl.value = null;
  }
  textContent.value = null;
  error.value = "";
}

function detectType(filename: string): "image" | "video" | "audio" | "text" | "pdf" | "unknown" {
  const ext = filename.split(".").pop()?.toLowerCase();
  if (["png", "jpg", "jpeg", "webp", "gif", "svg"].includes(ext || "")) return "image";
  if (["mp4", "webm", "mov"].includes(ext || "")) return "video";
  if (["mp3", "wav", "ogg", "m4a"].includes(ext || "")) return "audio";
  if (["txt", "md", "json", "js", "ts", "py", "html", "css"].includes(ext || "")) return "text";
  if (ext === "pdf") return "pdf";
  return "unknown";
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
    }>(`/api/v1/nodes/${node.id}/download`);

    // 2. Fetch encrypted bytes from R2
    const res = await fetch(downloadData.download_url);
    if (!res.ok) throw new Error("Failed to fetch file bytes from storage");
    const encryptedBuffer = await res.arrayBuffer();
    const encryptedBytes = new Uint8Array(encryptedBuffer);

    // 3. Unwrap File Key
    const fileKey = await unwrapKey(authStore.masterKey, downloadData.wrapped_file_key);
    const baseNonce = hexToUint8Array(downloadData.content_nonce);

    // 4. Decrypt content (chunk 1)
    const decryptedBytes = await decryptChunk(fileKey, encryptedBytes, baseNonce, 1);

    const type = detectType(node.name);
    fileType.value = type;

    if (type === "text") {
      textContent.value = new TextDecoder().decode(decryptedBytes);
    } else {
      const mime = type === "image" ? "image/jpeg" : type === "video" ? "video/mp4" : type === "audio" ? "audio/mpeg" : type === "pdf" ? "application/pdf" : "application/octet-stream";
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
  if (previewUrl.value && props.node) {
    const a = document.createElement("a");
    a.href = previewUrl.value;
    a.download = props.node.name;
    a.click();
  }
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
    <div class="w-full max-w-4xl max-h-[90vh] rounded-2xl overflow-hidden border border-slate-200 flex flex-col bg-white shadow-2xl">
      <!-- Header -->
      <div class="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
        <div class="flex items-center space-x-3 truncate">
          <FileText class="w-5 h-5 text-brand-600 shrink-0" />
          <span class="font-bold text-slate-900 text-sm truncate">{{ node?.name }}</span>
        </div>

        <div class="flex items-center space-x-2">
          <button
            v-if="previewUrl"
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
      <div class="flex-1 overflow-auto p-6 flex items-center justify-center min-h-[300px] bg-[#F8FAFC]">
        <div v-if="isLoading" class="flex flex-col items-center space-y-3 text-slate-500 text-xs">
          <Loader2 class="w-8 h-8 text-brand-600 animate-spin" />
          <span>Streaming & Decrypting file client-side...</span>
        </div>

        <div v-else-if="error" class="flex flex-col items-center space-y-2 text-rose-600 text-xs text-center max-w-md">
          <AlertCircle class="w-8 h-8 text-rose-500" />
          <span class="font-bold">Decryption Failed</span>
          <span class="text-slate-600">{{ error }}</span>
        </div>

        <!-- Render Image -->
        <img
          v-else-if="fileType === 'image' && previewUrl"
          :src="previewUrl"
          :alt="node?.name"
          class="max-w-full max-h-[70vh] object-contain rounded-xl shadow-md border border-slate-200 bg-white"
        />

        <!-- Render Video -->
        <video
          v-else-if="fileType === 'video' && previewUrl"
          :src="previewUrl"
          controls
          class="max-w-full max-h-[70vh] rounded-xl shadow-md border border-slate-200 bg-black"
        ></video>

        <!-- Render Audio -->
        <audio
          v-else-if="fileType === 'audio' && previewUrl"
          :src="previewUrl"
          controls
          class="w-full max-w-md"
        ></audio>

        <!-- Render Text / Code -->
        <pre
          v-else-if="fileType === 'text' && textContent"
          class="w-full p-4 rounded-xl bg-white border border-slate-200 font-mono text-xs text-slate-800 overflow-x-auto max-h-[65vh] leading-relaxed shadow-xs"
        ><code>{{ textContent }}</code></pre>

        <!-- Fallback -->
        <div v-else class="text-center space-y-3 text-slate-500 text-xs">
          <FileText class="w-12 h-12 mx-auto text-slate-400" />
          <p>Preview not supported in-browser for this format.</p>
          <button
            @click="handleDownload"
            class="btn-primary px-4 py-2 rounded-xl text-white font-semibold text-xs shadow-xs"
          >
            Download Decrypted File
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
