<script setup lang="ts">
import { ref } from "vue";
import { apiRequest } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import { generateLinkKey, wrapKey } from "../../lib/crypto/keys";
import { uint8ArrayToBase64 } from "../../lib/crypto/kdf";
import { X, Copy, Check, Link, Lock, Calendar, AlertCircle } from "lucide-vue-next";

const props = defineProps<{
  isOpen: boolean;
  node: any;
}>();

const emit = defineEmits(["close"]);

const authStore = useAuthStore();
const isGenerating = ref(false);
const shareUrl = ref<string | null>(null);
const copied = ref(false);
const requirePassword = ref(false);
const password = ref("");
const maxDownloads = ref<number | null>(null);
const errorMessage = ref("");

async function generatePublicLink() {
  if (!props.node) return;
  isGenerating.value = true;
  errorMessage.value = "";

  try {
    if (!authStore.masterKey) throw new Error("Vault is locked");

    // 1. Generate random 256-bit link key
    const linkKey = generateLinkKey();

    // 2. Wrap the node's File Key with this link key
    // For folder or file, wrap linkKey with masterKey for storage
    const wrappedKey = await wrapKey(authStore.masterKey, linkKey);

    // 3. Request share creation on backend
    const res = await apiRequest<{
      id: string;
      raw_token: string;
    }>("/api/v1/shares", {
      method: "POST",
      body: JSON.stringify({
        node_id: props.node.id,
        type: "link",
        wrapped_key: wrappedKey,
        permission: "download",
        password: requirePassword.value && password.value ? password.value : undefined,
        max_downloads: maxDownloads.value || undefined,
      }),
    });

    // 4. Construct URL with key in fragment (#)
    const linkKeyBase64 = uint8ArrayToBase64(linkKey);
    const origin = window.location.origin;
    shareUrl.value = `${origin}/s/${res.raw_token}#key=${encodeURIComponent(linkKeyBase64)}`;
  } catch (err: any) {
    errorMessage.value = err.message || "Failed to create share link.";
  } finally {
    isGenerating.value = false;
  }
}

function copyToClipboard() {
  if (!shareUrl.value) return;
  navigator.clipboard.writeText(shareUrl.value);
  copied.value = true;
  setTimeout(() => (copied.value = false), 2500);
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
    <div class="w-full max-w-lg rounded-2xl border border-slate-200 bg-white shadow-2xl p-6 space-y-5">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-2.5">
          <Link class="w-5 h-5 text-brand-600" />
          <h3 class="font-bold text-slate-900 text-base">Share File Securely</h3>
        </div>
        <button @click="emit('close')" class="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors">
          <X class="w-5 h-5" />
        </button>
      </div>

      <div class="text-xs text-slate-600">
        Sharing <strong class="text-slate-900">{{ node?.name }}</strong>. The decryption key will be stored exclusively in the URL fragment (<code class="text-brand-600 font-bold">#</code>) and will never touch our servers.
      </div>

      <div v-if="errorMessage" class="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">
        {{ errorMessage }}
      </div>

      <!-- Settings -->
      <div class="space-y-4 pt-1">
        <label class="flex items-center justify-between p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs cursor-pointer hover:bg-slate-100/70 transition-colors">
          <div class="flex items-center space-x-2 text-slate-800 font-medium">
            <Lock class="w-4 h-4 text-brand-600" />
            <span>Require Password</span>
          </div>
          <input type="checkbox" v-model="requirePassword" class="w-4 h-4 rounded text-brand-600 focus:ring-brand-500 border-slate-300" />
        </label>

        <div v-if="requirePassword" class="space-y-1">
          <input
            type="password"
            v-model="password"
            placeholder="Set link password..."
            class="w-full px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-900 focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 transition-all"
          />
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Max Downloads (Optional)</label>
          <input
            type="number"
            v-model.number="maxDownloads"
            placeholder="Unlimited"
            min="1"
            class="w-full px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-900 focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 transition-all"
          />
        </div>
      </div>

      <!-- Generated URL Box -->
      <div v-if="shareUrl" class="space-y-2 pt-1">
        <label class="block text-xs font-semibold text-brand-700">Encrypted Public Link</label>
        <div class="flex items-center space-x-2">
          <input
            type="text"
            readonly
            :value="shareUrl"
            class="flex-1 px-3.5 py-2.5 rounded-xl bg-slate-50 border border-brand-300 text-xs text-slate-800 font-mono select-all focus:outline-none focus:bg-white"
          />
          <button
            @click="copyToClipboard"
            class="btn-primary px-4 py-2.5 rounded-xl text-xs font-semibold text-white flex items-center space-x-1.5 transition-all shadow-xs"
          >
            <Check v-if="copied" class="w-4 h-4" />
            <Copy v-else class="w-4 h-4" />
            <span>{{ copied ? 'Copied' : 'Copy' }}</span>
          </button>
        </div>
      </div>

      <!-- Action -->
      <div class="pt-2">
        <button
          v-if="!shareUrl"
          @click="generatePublicLink"
          :disabled="isGenerating"
          class="btn-primary w-full py-3 rounded-xl font-semibold text-white text-xs disabled:opacity-50 transition-all shadow-sm hover:shadow-md"
        >
          {{ isGenerating ? 'Generating Encrypted Link...' : 'Create Zero-Knowledge Link' }}
        </button>
        <button
          v-else
          @click="emit('close')"
          class="w-full py-2.5 rounded-xl font-semibold text-slate-700 text-xs bg-slate-100 hover:bg-slate-200 transition-colors"
        >
          Done
        </button>
      </div>
    </div>
  </div>
</template>
