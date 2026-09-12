<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute } from "vue-router";
import { apiRequest } from "../../lib/api";
import { decryptFile } from "../../lib/crypto/content";
import { base64ToUint8Array, hexToUint8Array } from "../../lib/crypto/kdf";
import { Cloud, Lock, Download, AlertCircle, FileText, CheckCircle2 } from "lucide-vue-next";

const route = useRoute();
const token = route.params.token as string;

const isLoading = ref(true);
const shareInfo = ref<any>(null);
const passwordInput = ref("");
const requiresPassword = ref(false);
const error = ref("");
const isDownloading = ref(false);
const downloadSuccess = ref(false);

let linkKeyBytes: Uint8Array | null = null;

onMounted(async () => {
  // Extract key from fragment: #key=...
  const hash = window.location.hash;
  const match = hash.match(/key=([^&]+)/);
  if (match) {
    try {
      const decodedKeyBase64 = decodeURIComponent(match[1]);
      linkKeyBytes = base64ToUint8Array(decodedKeyBase64);
    } catch {
      error.value = "Invalid or corrupted decryption key in link fragment.";
    }
  }

  await loadShareInfo();
});

async function loadShareInfo(password?: string) {
  isLoading.value = true;
  error.value = "";
  try {
    const query = password ? `?password=${encodeURIComponent(password)}` : "";
    const info = await apiRequest(`/api/v1/public/shares/${token}${query}`);
    shareInfo.value = info;
    requiresPassword.value = info.requires_password && !info.is_authenticated;
  } catch (err: any) {
    error.value = err.message || "Failed to access shared link.";
  } finally {
    isLoading.value = false;
  }
}

async function unlockWithPassword() {
  if (!passwordInput.value) return;
  await loadShareInfo(passwordInput.value);
}

async function downloadAndDecrypt() {
  if (!linkKeyBytes) {
    error.value = "Missing decryption key in URL fragment (#key=...). Cannot decrypt without key.";
    return;
  }

  isDownloading.value = true;
  error.value = "";

  try {
    const pwQuery = passwordInput.value ? `?password=${encodeURIComponent(passwordInput.value)}` : "";
    const downloadData = await apiRequest(`/api/v1/public/shares/${token}/download${pwQuery}`);

    // Download encrypted payload
    const res = await fetch(downloadData.download_url);
    if (!res.ok) throw new Error("Failed to download encrypted bytes from storage.");

    const encryptedBuffer = await res.arrayBuffer();
    const encryptedBytes = new Uint8Array(encryptedBuffer);
    const baseNonce = hexToUint8Array(downloadData.content_nonce);

    // Decrypt content using linkKeyBytes (supports multi-chunk files)
    const partSize = downloadData.part_size || (8 * 1024 * 1024);
    const decryptedBytes = await decryptFile(linkKeyBytes, encryptedBytes, baseNonce, partSize);

    // Trigger browser file download
    const blob = new Blob([decryptedBytes], { type: "application/octet-stream" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Decrypted-File-${token.slice(0, 8)}`;
    a.click();
    URL.revokeObjectURL(url);
    downloadSuccess.value = true;
  } catch (err: any) {
    error.value = err.message || "Decryption failed.";
  } finally {
    isDownloading.value = false;
  }
}
</script>

<template>
  <div class="min-h-screen bg-[#F8FAFC] flex flex-col justify-center py-12 sm:px-6 lg:px-8 text-slate-800 selection:bg-brand-600 selection:text-white">
    <div class="sm:mx-auto sm:w-full sm:max-w-md text-center space-y-3">
      <router-link to="/" class="inline-flex items-center space-x-2.5">
        <div class="w-10 h-10 rounded-xl bg-brand-600 flex items-center justify-center shadow-md shadow-brand-500/20 text-white">
          <Lock class="w-5 h-5" />
        </div>
        <div class="flex flex-col text-left">
          <span class="text-xl font-bold tracking-tight text-slate-900 leading-none">SmartSpace</span>
          <span class="text-[9px] text-slate-500 font-mono">smartspacedata.com</span>
        </div>
      </router-link>
      <h2 class="text-xl font-bold text-slate-900">Shared Encrypted File</h2>
      <p class="text-xs text-slate-500">Zero-knowledge client-side decryption executing in your browser.</p>
    </div>

    <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
      <div class="bg-white p-8 rounded-2xl border border-slate-200 shadow-xl space-y-6">
        <div v-if="error" class="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center space-x-2">
          <AlertCircle class="w-4 h-4 shrink-0 text-rose-600" />
          <span>{{ error }}</span>
        </div>

        <div v-if="isLoading" class="text-center py-8 text-slate-500 text-xs">
          Loading share information...
        </div>

        <!-- Password Protected View -->
        <div v-else-if="requiresPassword" class="space-y-4">
          <div class="text-center space-y-2">
            <Lock class="w-8 h-8 text-brand-600 mx-auto" />
            <div class="text-sm font-bold text-slate-900">Password Protected Link</div>
            <p class="text-xs text-slate-500">Enter the password provided by the file owner to proceed.</p>
          </div>

          <form @submit.prevent="unlockWithPassword" class="space-y-3">
            <input
              type="password"
              v-model="passwordInput"
              required
              placeholder="Enter password..."
              class="w-full px-4 py-3 rounded-xl bg-slate-50 border border-slate-200 text-sm text-slate-900 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 transition-all"
            />
            <button
              type="submit"
              class="btn-primary w-full py-3 rounded-xl font-semibold text-white text-xs shadow-sm hover:shadow-md"
            >
              Unlock Share Link
            </button>
          </form>
        </div>

        <!-- Ready to Download View -->
        <div v-else-if="shareInfo" class="space-y-6">
          <div class="p-5 rounded-2xl bg-slate-50 border border-slate-200 text-center space-y-3">
            <div class="w-12 h-12 rounded-xl bg-blue-50 text-brand-600 flex items-center justify-center mx-auto border border-blue-200">
              <FileText class="w-6 h-6" />
            </div>
            <div>
              <div class="text-sm font-bold text-slate-900">Encrypted File Ready</div>
              <div class="text-xs text-slate-500 font-mono mt-1">
                {{ (shareInfo.size_bytes / (1024 * 1024)).toFixed(1) }} MB • AES-256-GCM
              </div>
            </div>
          </div>

          <div v-if="downloadSuccess" class="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center space-x-2">
            <CheckCircle2 class="w-4 h-4 shrink-0 text-emerald-600" />
            <span>Decrypted and downloaded successfully!</span>
          </div>

          <button
            @click="downloadAndDecrypt"
            :disabled="isDownloading"
            class="btn-primary w-full py-3.5 rounded-xl font-semibold text-white disabled:opacity-50 text-xs shadow-md hover:shadow-lg flex items-center justify-center space-x-2 transition-all"
          >
            <Download class="w-4 h-4" />
            <span>{{ isDownloading ? 'Streaming & Decrypting...' : 'Decrypt & Download File' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
