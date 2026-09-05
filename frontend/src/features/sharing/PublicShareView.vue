<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute } from "vue-router";
import { apiRequest } from "../../lib/api";
import { decryptChunk } from "../../lib/crypto/content";
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

    // Decrypt content chunk using linkKeyBytes
    const decryptedBytes = await decryptChunk(linkKeyBytes, encryptedBytes, baseNonce, 1);

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
  <div class="min-h-screen bg-[#070D1A] flex flex-col justify-center py-12 sm:px-6 lg:px-8 text-slate-100">
    <div class="sm:mx-auto sm:w-full sm:max-w-md text-center space-y-3">
      <router-link to="/" class="inline-flex items-center space-x-2">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-accent-orange flex items-center justify-center shadow-lg shadow-brand-500/20">
          <Cloud class="w-6 h-6 text-white fill-white/20" />
        </div>
        <span class="text-2xl font-black text-white">SpeedCloud</span>
      </router-link>
      <h2 class="text-xl font-bold text-white">Shared Encrypted File</h2>
      <p class="text-xs text-slate-400">Zero-knowledge client-side decryption.</p>
    </div>

    <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
      <div class="glass-panel p-8 rounded-3xl border border-slate-800 shadow-2xl space-y-6">
        <div v-if="error" class="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-2">
          <AlertCircle class="w-4 h-4 shrink-0" />
          <span>{{ error }}</span>
        </div>

        <div v-if="isLoading" class="text-center py-8 text-slate-400 text-xs">
          Loading share information...
        </div>

        <!-- Password Protected View -->
        <div v-else-if="requiresPassword" class="space-y-4">
          <div class="text-center space-y-2">
            <Lock class="w-8 h-8 text-brand-400 mx-auto" />
            <div class="text-sm font-bold text-white">Password Protected Link</div>
            <p class="text-xs text-slate-400">Enter the password provided by the file owner to proceed.</p>
          </div>

          <form @submit.prevent="unlockWithPassword" class="space-y-3">
            <input
              type="password"
              v-model="passwordInput"
              required
              placeholder="Enter password..."
              class="w-full px-4 py-3 rounded-xl bg-slate-900 border border-slate-700 text-sm text-white focus:outline-none focus:border-brand-500"
            />
            <button
              type="submit"
              class="w-full py-3 rounded-xl font-bold text-white bg-brand-600 hover:bg-brand-500 text-xs shadow-md"
            >
              Unlock Share Link
            </button>
          </form>
        </div>

        <!-- Ready to Download View -->
        <div v-else-if="shareInfo" class="space-y-6">
          <div class="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 text-center space-y-3">
            <div class="w-12 h-12 rounded-xl bg-brand-500/10 border border-brand-500/30 text-brand-400 flex items-center justify-center mx-auto">
              <FileText class="w-6 h-6" />
            </div>
            <div>
              <div class="text-sm font-bold text-white">Encrypted File Ready</div>
              <div class="text-xs text-slate-400 font-mono mt-1">
                {{ (shareInfo.size_bytes / (1024 * 1024)).toFixed(1) }} MB • AES-256-GCM
              </div>
            </div>
          </div>

          <div v-if="downloadSuccess" class="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center space-x-2">
            <CheckCircle2 class="w-4 h-4 shrink-0 text-emerald-400" />
            <span>Decrypted and downloaded successfully!</span>
          </div>

          <button
            @click="downloadAndDecrypt"
            :disabled="isDownloading"
            class="w-full py-3.5 rounded-xl font-bold text-white bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-xs shadow-lg shadow-brand-600/30 flex items-center justify-center space-x-2 transition-all"
          >
            <Download class="w-4 h-4" />
            <span>{{ isDownloading ? 'Streaming & Decrypting...' : 'Decrypt & Download File' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
