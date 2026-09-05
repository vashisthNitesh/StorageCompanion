<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { useFilesStore } from "../stores/files";
import { useUploadStore } from "../stores/upload";
import {
  Lock,
  Folder,
  Share2,
  Settings,
  CreditCard,
  LogOut,
  UploadCloud,
  Search,
  ChevronRight,
  Shield,
  HardDrive,
  AlertTriangle,
} from "lucide-vue-next";
import UploadTray from "../features/files/UploadTray.vue";

const router = useRouter();
const authStore = useAuthStore();
const filesStore = useFilesStore();
const uploadStore = useUploadStore();

const searchInput = ref("");
const fileInputRef = ref<HTMLInputElement | null>(null);

const storageUsedMB = computed(() => {
  const bytes = authStore.user?.quota?.bytes_used || 0;
  return (bytes / (1024 * 1024)).toFixed(1);
});

const storageLimitGB = computed(() => {
  const bytes = authStore.user?.quota?.bytes_limit || 0;
  return (bytes / (1024 * 1024 * 1024)).toFixed(0);
});

const percentUsed = computed(() => {
  return authStore.user?.quota?.percent_used || 0;
});

function handleUploadClick() {
  if (!authStore.hasActiveSubscription) {
    router.push({ path: "/app/billing", query: { gate: "required" } });
    return;
  }
  fileInputRef.value?.click();
}

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement;
  if (target.files) {
    Array.from(target.files).forEach((file) => {
      uploadStore.uploadFile(file, filesStore.currentParentId);
    });
    target.value = "";
  }
}

async function handleLogout() {
  await authStore.logout();
  router.push("/");
}

function onSearch() {
  filesStore.performSearch(searchInput.value);
}

onMounted(() => {
  if (authStore.isAuthenticated && !authStore.isVaultUnlocked) {
    // Demo auto-unlock for test user
    if (authStore.user?.email === "demo@speedcloud.local") {
      authStore.unlockVault("SpeedCloud2026!").then(() => {
        if (authStore.hasActiveSubscription) {
          filesStore.fetchNodes();
        }
      }).catch(() => {});
    }
  } else if (authStore.isVaultUnlocked && authStore.hasActiveSubscription) {
    filesStore.fetchNodes();
  }
});
</script>

<template>
  <div class="flex h-screen bg-surface-ground text-slate-100 overflow-hidden selection:bg-brand-600 selection:text-white">
    <!-- Left Sidebar -->
    <aside class="w-64 border-r border-surface-border bg-surface-card flex flex-col justify-between shrink-0">
      <div class="p-4 space-y-5">
        <!-- Logo -->
        <router-link to="/" class="flex items-center space-x-2.5">
          <div class="w-7 h-7 rounded-lg bg-brand-600 border border-white/20 flex items-center justify-center shadow-sm">
            <Lock class="w-3.5 h-3.5 text-white" />
          </div>
          <div>
            <div class="font-bold text-white text-sm tracking-tight leading-none">SpeedCloud</div>
            <div class="text-[10px] text-slate-400 font-mono mt-0.5">Encrypted Vault</div>
          </div>
        </router-link>

        <!-- Quick Upload Action -->
        <div>
          <input ref="fileInputRef" type="file" multiple class="hidden" @change="handleFileSelect" />
          <button
            @click="handleUploadClick"
            class="w-full btn-primary py-2.5 px-3 rounded-lg text-xs font-semibold text-white flex items-center justify-center space-x-2 shadow-sm"
          >
            <UploadCloud class="w-4 h-4" />
            <span>Upload Encrypted Files</span>
          </button>
        </div>

        <!-- Navigation Links -->
        <nav class="space-y-1 text-xs font-medium text-slate-300">
          <router-link
            to="/app/files"
            class="flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-surface-elevated hover:text-white transition-colors"
            :class="{ 'bg-surface-elevated text-white font-semibold border border-surface-border': $route.path === '/app/files' }"
          >
            <Folder class="w-4 h-4 text-slate-400" />
            <span>Encrypted Vault</span>
          </router-link>

          <router-link
            to="/app/shared"
            class="flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-surface-elevated hover:text-white transition-colors"
            :class="{ 'bg-surface-elevated text-white font-semibold border border-surface-border': $route.path === '/app/shared' }"
          >
            <Share2 class="w-4 h-4 text-slate-400" />
            <span>Shared Links</span>
          </router-link>

          <router-link
            to="/app/billing"
            class="flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-surface-elevated hover:text-white transition-colors"
            :class="{ 'bg-surface-elevated text-white font-semibold border border-surface-border': $route.path === '/app/billing' }"
          >
            <CreditCard class="w-4 h-4 text-slate-400" />
            <span>Subscription & Billing</span>
          </router-link>

          <router-link
            to="/app/settings"
            class="flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-surface-elevated hover:text-white transition-colors"
            :class="{ 'bg-surface-elevated text-white font-semibold border border-surface-border': $route.path === '/app/settings' }"
          >
            <Settings class="w-4 h-4 text-slate-400" />
            <span>Security & Sessions</span>
          </router-link>
        </nav>
      </div>

      <!-- Storage Meter & Profile Footer -->
      <div class="p-4 border-t border-surface-border space-y-4">
        <!-- Storage Quota Meter -->
        <div class="p-3 rounded-xl bg-surface-elevated border border-surface-border space-y-2">
          <div class="flex items-center justify-between text-xs">
            <div class="flex items-center space-x-1.5 text-slate-300 font-medium">
              <HardDrive class="w-3.5 h-3.5 text-brand-400" />
              <span>Storage Quota</span>
            </div>
            <span class="font-mono text-slate-400 text-[10px]">{{ percentUsed }}%</span>
          </div>

          <div class="w-full bg-surface-subtle h-1.5 rounded-full overflow-hidden">
            <div
              class="h-full rounded-full transition-all duration-300"
              :class="percentUsed > 85 ? 'bg-rose-500' : 'bg-brand-600'"
              :style="{ width: `${percentUsed}%` }"
            ></div>
          </div>

          <div class="flex items-center justify-between text-[10px] text-slate-400">
            <span>{{ storageUsedMB }} MB of {{ storageLimitGB }} GB</span>
            <router-link to="/app/billing" class="text-brand-400 hover:underline">
              Manage
            </router-link>
          </div>
        </div>

        <!-- User Profile Row -->
        <div class="flex items-center justify-between pt-1">
          <div class="flex items-center space-x-2.5 min-w-0">
            <div class="w-7 h-7 rounded-full bg-brand-600/30 border border-brand-500/40 text-brand-300 flex items-center justify-center font-bold text-xs shrink-0">
              {{ (authStore.user?.full_name || authStore.user?.email || 'U')[0].toUpperCase() }}
            </div>
            <div class="min-w-0">
              <div class="text-xs font-semibold text-white truncate">
                {{ authStore.user?.full_name || 'My Vault' }}
              </div>
              <div class="text-[10px] text-slate-400 truncate">
                {{ authStore.user?.email }}
              </div>
            </div>
          </div>

          <button
            @click="handleLogout"
            class="p-1.5 text-slate-400 hover:text-rose-400 rounded-lg transition-colors"
            title="Sign out"
          >
            <LogOut class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </aside>

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <!-- Unpaid Warning Banner -->
      <div
        v-if="!authStore.hasActiveSubscription"
        class="px-6 py-2.5 bg-amber-950/70 border-b border-amber-800/60 flex items-center justify-between text-xs text-amber-200"
      >
        <div class="flex items-center space-x-2">
          <AlertTriangle class="w-4 h-4 text-amber-400 shrink-0" />
          <span>Subscription Inactive: Complete your plan subscription with Razorpay to unlock your encrypted storage.</span>
        </div>
        <router-link
          to="/app/billing"
          class="px-2.5 py-1 rounded bg-amber-500/20 text-amber-300 font-bold hover:bg-amber-500/30 transition-colors shrink-0"
        >
          Subscribe Now →
        </router-link>
      </div>

      <!-- Top Header -->
      <header class="h-14 border-b border-surface-border bg-surface-card/60 backdrop-blur-md flex items-center justify-between px-6 shrink-0">
        <!-- Breadcrumbs -->
        <div class="flex items-center space-x-2 text-xs font-medium text-slate-400">
          <template v-for="(crumb, idx) in filesStore.breadcrumbs" :key="crumb.id || idx">
            <button
              @click="filesStore.navigateUp(idx)"
              class="hover:text-white transition-colors"
              :class="{ 'text-white font-semibold': idx === filesStore.breadcrumbs.length - 1 }"
            >
              {{ crumb.name }}
            </button>
            <ChevronRight v-if="idx < filesStore.breadcrumbs.length - 1" class="w-3.5 h-3.5 text-slate-600" />
          </template>
        </div>

        <!-- Search & Status -->
        <div class="flex items-center space-x-3">
          <!-- Client-side decrypted search input -->
          <div class="relative w-64">
            <Search class="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              v-model="searchInput"
              @input="onSearch"
              placeholder="Search decrypted vault..."
              class="w-full pl-8 pr-3 py-1.5 rounded-lg bg-surface-ground border border-surface-border text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-brand-500"
            />
          </div>

          <!-- Subscription Badge -->
          <div
            class="px-2.5 py-1 rounded-md text-[10px] font-mono font-bold uppercase tracking-wider flex items-center space-x-1"
            :class="authStore.hasActiveSubscription ? 'bg-emerald-950/60 text-accent-emerald border border-emerald-800/60' : 'bg-amber-950/60 text-amber-300 border border-amber-800/60'"
          >
            <span>{{ authStore.hasActiveSubscription ? (authStore.user?.subscription?.plan_name || 'Active Plan') : 'Unpaid' }}</span>
          </div>
        </div>
      </header>

      <!-- Routed Page Container -->
      <main class="flex-1 overflow-y-auto p-6 bg-surface-ground">
        <router-view />
      </main>

      <!-- Floating Upload Tray -->
      <UploadTray />
    </div>
  </div>
</template>
