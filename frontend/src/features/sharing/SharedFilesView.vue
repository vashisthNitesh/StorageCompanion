<script setup lang="ts">
import { ref, onMounted } from "vue";
import { apiRequest } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import { decryptName } from "../../lib/crypto/names";
import { Share2, Link, Trash2, ExternalLink, ShieldCheck } from "lucide-vue-next";

const shares = ref<any[]>([]);
const isLoading = ref(true);
const loadError = ref("");
const authStore = useAuthStore();

// Names are end-to-end encrypted; the API only returns ciphertext (node_details.encrypted_name),
// so the list used to fall back to printing the raw node UUID.
async function displayName(share: any): Promise<string> {
  const nd = share.node_details;
  if (!nd?.encrypted_name || !authStore.masterKey) return "Encrypted file (unlock vault to see name)";
  try {
    return await decryptName(authStore.masterKey, nd.encrypted_name, nd.name_nonce);
  } catch {
    return "Encrypted file";
  }
}

onMounted(async () => {
  await fetchShares();
});

async function fetchShares() {
  isLoading.value = true;
  try {
    loadError.value = "";
    const data = await apiRequest("/api/v1/shares");
    const list = Array.isArray(data) ? data : data.results || [];
    shares.value = await Promise.all(list.map(async (s: any) => ({ ...s, display_name: await displayName(s) })));
  } catch (err: any) {
    loadError.value = err?.message || "Could not load your shared links.";
  } finally {
    isLoading.value = false;
  }
}

async function revokeShare(id: string) {
  try {
    await apiRequest(`/api/v1/shares/${id}`, { method: "DELETE" });
    shares.value = shares.value.filter((s) => s.id !== id);
  } catch (err: any) {
    loadError.value = err?.message || "Could not revoke the link.";
  }
}
</script>

<template>
  <div class="space-y-6 max-w-5xl">
    <div>
      <h1 class="text-xl font-bold text-slate-900">Active Shared Links</h1>
      <p class="text-xs text-slate-500">Zero-knowledge links created by you. Keys reside in the URL fragment.</p>
    </div>

    <div v-if="loadError" class="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">{{ loadError }}</div>

    <div v-if="isLoading" class="text-xs text-slate-500">
      Loading shared items...
    </div>

    <div v-else-if="shares.length === 0" class="p-12 text-center rounded-2xl border border-dashed border-slate-200 bg-white shadow-xs space-y-3">
      <Share2 class="w-10 h-10 text-slate-400 mx-auto" />
      <div class="text-sm font-bold text-slate-900">No active shares</div>
      <p class="text-xs text-slate-500 max-w-xs mx-auto">
        Open the ⋮ menu on any file in My Files and choose Share to create a secure link.
      </p>
    </div>

    <div v-else class="rounded-2xl border border-slate-200 bg-white divide-y divide-slate-100 shadow-xs">
      <div
        v-for="share in shares"
        :key="share.id"
        class="p-4 flex items-center justify-between text-xs"
      >
        <div class="flex items-center space-x-3">
          <div class="w-9 h-9 rounded-xl bg-blue-50 text-brand-600 flex items-center justify-center border border-blue-100">
            <Link class="w-4 h-4" />
          </div>
          <div>
            <div class="font-bold text-slate-900">{{ share.display_name }}</div>
            <div class="text-[11px] text-slate-500 flex items-center space-x-2 mt-0.5 font-mono">
              <span>Downloads: {{ share.download_count }} / {{ share.max_downloads || '∞' }}</span>
              <span v-if="share.has_password" class="text-amber-700 font-bold">• Password Protected</span>
            </div>
          </div>
        </div>

        <button
          @click="revokeShare(share.id)"
          class="px-3 py-1.5 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 flex items-center space-x-1.5 transition-colors font-medium text-xs"
        >
          <Trash2 class="w-3.5 h-3.5" />
          <span>Revoke</span>
        </button>
      </div>
    </div>
  </div>
</template>
