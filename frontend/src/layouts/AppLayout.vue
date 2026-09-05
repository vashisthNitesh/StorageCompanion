<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { useFilesStore } from "../stores/files";
import { useUploadStore } from "../stores/upload";
import {
  Cloud,
  Folder,
  Share2,
  Clock,
  Star,
  Trash2,
  HardDrive,
  Settings,
  CreditCard,
  LogOut,
  UploadCloud,
  FolderPlus,
  Search,
  ChevronRight,
  Shield,
  Zap,
} from "lucide-vue-next";

const router = useRouter();
const authStore = useAuthStore();
const filesStore = useFilesStore();
const uploadStore = useUploadStore();

const searchInput = ref("");
const fileInputRef = ref<HTMLInputElement | null>(null);
const folderInputRef = ref<HTMLInputElement | null>(null);

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

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement;
  if (target.files) {
    Array.from(target.files).forEach((file) => {
      uploadStore.uploadFile(file, filesStore.currentParentId);
    });
    target.value = "";
  }
}

function handleFolderSelect(event: Event) {
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
    // In demo or test mode if masterKey isn't in memory, restore demo key if demo user
    if (authStore.user?.email === "demo@speedcloud.local") {
      authStore.unlockVault("SpeedCloud2026!").then(() => {
        filesStore.fetchNodes();
      }).catch(() => {});
    }
  } else if (authStore.isVaultUnlocked) {
    filesStore.fetchNodes();
  }
});
</script>

<template>
  <div class="flex h-screen bg-[#070D1A] text-slate-100 overflow-hidden">
    <!-- Left Sidebar -->
    <aside class="w-64 border-r border-slate-800/80 bg-[#080E1C] flex flex-col justify-between shrink-0">
      <div class="p-5 space-y-6">
        <!-- Logo -->
        <router-link to="/" class="flex items-center space-x-3">
          <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-600 to-accent-orange flex items-center justify-center shadow-md">
            <Cloud class="w-5 h-5 text-white fill-white/20" />
          </div>
          <div>
            <div class="font-extrabold text-white text-lg tracking-tight leading-none">SpeedCloud</div>
            <div class="text-[10px] text-brand-400 font-mono">Zero-Knowledge Vault</div>
          </div>
        </router-link>

        <!-- Quick Upload Action -->
        <div class="space-y-2">
          <input ref="fileInputRef" type="file" multiple class="hidden" @change="handleFileSelect" />
          <input ref="folderInputRef" type="file" webkitdirectory class="hidden" @change="handleFolderSelect" />

          <button
            @click="fileInputRef?.click()"
            class="w-full py-2.5 px-4 rounded-xl font-semibold text-xs text-white bg-brand-600 hover:bg-brand-500 shadow-md shadow-brand-600/20 transition-all flex items-center justify-center space-x-2"
          >
            <UploadCloud class="w-4 h-4" />
            <span>Upload Encrypted Files</span>
          </button>
        </div>

        <!-- Navigation Links -->
        <nav class="space-y-1 text-xs font-semibold text-slate-300">
          <router-link
            to="/app/files"
            class="flex items-center space-x-3 px-3.5 py-2.5 rounded-xl hover:bg-slate-800/60 hover:text-white transition-colors"
            :class="{ 'bg-brand-600/15 text-brand-400 border border-brand-500/20': $route.path === '/app/files' }"
          >
            <Folder class="w-4 h-4" />
            <span>My Files</span>
          </router-link>

          <router-link
            to="/app/shared"
            class="flex items-center space-x-3 px-3.5 py-2.5 rounded-xl hover:bg-slate-800/60 hover:text-white transition-colors"
            :class="{ 'bg-brand-600/15 text-brand-400 border border-brand-500/20': $route.path === '/app/shared' }"
          >
            <Share2 class="w-4 h-4" />
            <span>Shared Links</span>
          </router-link>

          <router-link
            to="/app/billing"
            class="flex items-center space-x-3 px-3.5 py-2.5 rounded-xl hover:bg-slate-800/60 hover:text-white transition-colors"
            :class="{ 'bg-brand-600/15 text-brand-400 border border-brand-500/20': $route.path === '/app/billing' }"
          >
            <CreditCard class="w-4 h-4" />
            <span>Subscription & Plan</span>
          </router-link>

          <router-link
            to="/app/settings"
            class="flex items-center space-x-3 px-3.5 py-2.5 rounded-xl hover:bg-slate-800/60 hover:text-white transition-colors"
            :class="{ 'bg-brand-600/15 text-brand-400 border border-brand-500/20': $route.path === '/app/settings' }"
          >
            <Settings class="w-4 h-4" />
            <span>Security & Sessions</span>
          </router-link>
        </nav>
      </div>

      <!-- Storage Meter and Profile Widget -->
      <div class="p-5 border-t border-slate-800/80 space-y-4">
        <!-- Storage Quota Meter -->
        <div class="p-3.5 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-2">
          <div class="flex items-center justify-between text-xs">
            <div class="flex items-center space-x-1.5 text-slate-300 font-semibold">
              <HardDrive class="w-3.5 h-3.5 text-brand-400" />
              <span>Storage Usage</span>
            </div>
            <span class="font-mono text-slate-400 text-[10px]">{{ percentUsed }}%</span>
          </div>

          <div class="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
            <div
              class="h-full rounded-full transition-all duration-300"
              :class="percentUsed > 85 ? 'bg-rose-500' : 'bg-brand-500'"
              :style="{ width: `${percentUsed}%` }"
            ></div>
          </div>

          <div class="flex items-center justify-between text-[11px] text-slate-400">
            <span>{{ storageUsedMB }} MB of {{ storageLimitGB }} GB</span>
            <router-link to="/app/billing" class="text-brand-400 font-bold hover:underline">
              Upgrade
            </router-link>
          </div>
        </div>

        <!-- User Profile Row -->
        <div class="flex items-center justify-between pt-1">
          <div class="flex items-center space-x-2.5 min-w-0">
            <div class="w-8 h-8 rounded-full bg-brand-600 text-white flex items-center justify-center font-bold text-xs shrink-0">
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
            <LogOut class="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>

    <!-- Main Content Shell -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <!-- Top Bar -->
      <header class="h-16 border-b border-slate-800/80 bg-[#070D1A]/80 flex items-center justify-between px-6 shrink-0">
        <!-- Breadcrumbs -->
        <div class="flex items-center space-x-2 text-xs font-medium text-slate-400">
          <template v-for="(crumb, idx) in filesStore.breadcrumbs" :key="crumb.id || idx">
            <button
              @click="filesStore.navigateUp(idx)"
              class="hover:text-white transition-colors"
              :class="{ 'text-white font-bold': idx === filesStore.breadcrumbs.length - 1 }"
            >
              {{ crumb.name }}
            </button>
            <ChevronRight v-if="idx < filesStore.breadcrumbs.length - 1" class="w-3.5 h-3.5 text-slate-600" />
          </template>
        </div>

        <!-- Right actions (Search & Create Folder) -->
        <div class="flex items-center space-x-3">
          <!-- Client-side decrypted search input -->
          <div class="relative w-64">
            <Search class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              v-model="searchInput"
              @input="onSearch"
              placeholder="Search decrypted index (/)..."
              class="w-full pl-9 pr-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-brand-500"
            />
          </div>

          <!-- Subscription Badge -->
          <div class="px-2.5 py-1 rounded-lg bg-brand-950/80 border border-brand-800/50 text-[11px] font-bold text-brand-400 flex items-center space-x-1">
            <Zap class="w-3 h-3 text-accent-orange" />
            <span>{{ authStore.user?.subscription?.plan_name || 'Active Plan' }}</span>
          </div>
        </div>
      </header>

      <!-- Subscribed Content Pane -->
      <main class="flex-1 overflow-y-auto p-6 bg-[#070D1A]">
        <router-view />
      </main>
    </div>
  </div>
</template>
