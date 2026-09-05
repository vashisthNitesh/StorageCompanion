<script setup lang="ts">
import { ref, onMounted } from "vue";
import { apiRequest } from "../../lib/api";
import { Share2, Link, Trash2, ExternalLink, ShieldCheck } from "lucide-vue-next";

const shares = ref<any[]>([]);
const isLoading = ref(true);

onMounted(async () => {
  await fetchShares();
});

async function fetchShares() {
  isLoading.value = true;
  try {
    const data = await apiRequest("/api/v1/shares");
    shares.value = Array.isArray(data) ? data : data.results || [];
  } finally {
    isLoading.value = false;
  }
}

async function revokeShare(id: string) {
  await apiRequest(`/api/v1/shares/${id}`, { method: "DELETE" });
  shares.value = shares.value.filter((s) => s.id !== id);
}
</script>

<template>
  <div class="space-y-6 max-w-5xl">
    <div>
      <h1 class="text-xl font-bold text-white">Active Shared Links</h1>
      <p class="text-xs text-slate-400">Zero-knowledge links created by you. Keys reside in the URL fragment.</p>
    </div>

    <div v-if="isLoading" class="text-xs text-slate-400">
      Loading shared items...
    </div>

    <div v-else-if="shares.length === 0" class="p-12 text-center rounded-3xl border border-dashed border-slate-800 bg-slate-900/20 space-y-3">
      <Share2 class="w-10 h-10 text-slate-600 mx-auto" />
      <div class="text-sm font-bold text-white">No active shares</div>
      <p class="text-xs text-slate-400 max-w-xs mx-auto">
        Right click on any file in My Files to generate a secure public link.
      </p>
    </div>

    <div v-else class="rounded-2xl border border-slate-800 bg-slate-900/40 divide-y divide-slate-800/60">
      <div
        v-for="share in shares"
        :key="share.id"
        class="p-4 flex items-center justify-between text-xs"
      >
        <div class="flex items-center space-x-3">
          <div class="w-9 h-9 rounded-xl bg-brand-500/10 text-brand-400 flex items-center justify-center">
            <Link class="w-4 h-4" />
          </div>
          <div>
            <div class="font-bold text-white">Node: {{ share.node_details?.name || share.node }}</div>
            <div class="text-[11px] text-slate-400 flex items-center space-x-2 mt-0.5 font-mono">
              <span>Downloads: {{ share.download_count }} / {{ share.max_downloads || '∞' }}</span>
              <span v-if="share.has_password" class="text-amber-400 font-bold">• Password Protected</span>
            </div>
          </div>
        </div>

        <button
          @click="revokeShare(share.id)"
          class="px-3 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 flex items-center space-x-1.5 transition-colors font-medium"
        >
          <Trash2 class="w-3.5 h-3.5" />
          <span>Revoke</span>
        </button>
      </div>
    </div>
  </div>
</template>
