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
  ShieldAlert,
  HardDrive,
  AlertTriangle,
  ArrowRight,
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
  if (authStore.isVaultUnlocked && authStore.hasActiveSubscription) {
    filesStore.fetchNodes();
  }
});
</script>

<template>
  <div class="flex h-screen bg-slate-50 text-slate-900 overflow-hidden selection:bg-brand-600 selection:text-white">
    <!-- Left Sidebar -->
    <aside class="w-64 border-r border-slate-200 bg-white flex flex-col justify-between shrink-0 shadow-[1px_0_3px_0_rgba(0,0,0,0.02)]">
      <div class="p-4 space-y-5">
        <!-- Logo -->
        <router-link to="/" class="flex items-center space-x-2.5 group">
          <div class="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-sm shadow-blue-500/20 group-hover:scale-105 transition-transform">
            <Lock class="w-4 h-4 text-white" />
          </div>
          <div>
            <div class="font-bold text-slate-900 text-sm tracking-tight leading-none">SmartSpace</div>
            <div class="text-[10px] text-slate-500 font-medium mt-0.5">smartspacedata.com</div>
          </div>
        </router-link>

        <!-- Quick Upload Action -->
        <div>
          <input ref="fileInputRef" type="file" multiple class="hidden" @change="handleFileSelect" />
          <button
            @click="handleUploadClick"
            class="w-full btn-primary py-2.5 px-3 rounded-xl text-xs font-semibold flex items-center justify-center space-x-2"
          >
            <UploadCloud class="w-4 h-4" />
            <span>Upload Encrypted Files</span>
          </button>
        </div>

        <!-- Navigation Links -->
        <nav class="space-y-1 text-xs font-medium">
          <router-link
            to="/app/files"
            class="flex items-center space-x-3 px-3 py-2 rounded-xl transition-all"
            :class="$route.path === '/app/files' ? 'bg-blue-50 text-blue-700 font-semibold' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70'"
          >
            <Folder class="w-4 h-4" :class="$route.path === '/app/files' ? 'text-blue-600' : 'text-slate-400'" />
            <span>Encrypted Vault</span>
          </router-link>

          <router-link
            to="/app/shared"
            class="flex items-center space-x-3 px-3 py-2 rounded-xl transition-all"
            :class="$route.path === '/app/shared' ? 'bg-blue-50 text-blue-700 font-semibold' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70'"
          >
            <Share2 class="w-4 h-4" :class="$route.path === '/app/shared' ? 'text-blue-600' : 'text-slate-400'" />
            <span>Shared Links</span>
          </router-link>

          <router-link
            to="/app/billing"
            class="flex items-center space-x-3 px-3 py-2 rounded-xl transition-all"
            :class="$route.path === '/app/billing' ? 'bg-blue-50 text-blue-700 font-semibold' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70'"
          >
            <CreditCard class="w-4 h-4" :class="$route.path === '/app/billing' ? 'text-blue-600' : 'text-slate-400'" />
            <span>Subscription & Billing</span>
          </router-link>

          <router-link
            to="/app/settings"
            class="flex items-center space-x-3 px-3 py-2 rounded-xl transition-all"
            :class="$route.path === '/app/settings' ? 'bg-blue-50 text-blue-700 font-semibold' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70'"
          >
            <Settings class="w-4 h-4" :class="$route.path === '/app/settings' ? 'text-blue-600' : 'text-slate-400'" />
            <span>Security & Sessions</span>
          </router-link>

          <!-- Master Admin Portal (Restricted to Superusers / Staff) -->
          <router-link
            v-if="authStore.isMasterAdmin"
            to="/app/admin"
            class="flex items-center space-x-3 px-3 py-2 rounded-xl transition-all border border-indigo-200/70"
            :class="$route.path.startsWith('/app/admin') ? 'bg-indigo-50 text-indigo-800 font-bold shadow-xs' : 'bg-indigo-50/40 text-indigo-700 hover:bg-indigo-100/60'"
          >
            <ShieldAlert class="w-4 h-4 text-indigo-600 shrink-0" />
            <div class="flex items-center justify-between w-full min-w-0">
              <span class="truncate">Admin Portal</span>
              <span class="text-[9px] bg-indigo-600 text-white px-1.5 py-0.5 rounded font-mono font-bold uppercase tracking-wider">Master</span>
            </div>
          </router-link>
        </nav>
      </div>

      <!-- Storage Meter & Profile Footer -->
      <div class="p-4 border-t border-slate-200 space-y-3.5 bg-slate-50/50">
        <!-- Storage Quota Meter: Displayed strictly for regular customers -->
        <div v-if="!authStore.isMasterAdmin" class="p-3 rounded-xl bg-white border border-slate-200 shadow-2xs space-y-2">
          <div class="flex items-center justify-between text-xs">
            <div class="flex items-center space-x-1.5 text-slate-700 font-medium">
              <HardDrive class="w-3.5 h-3.5 text-blue-600" />
              <span>Storage Quota</span>
            </div>
            <span class="font-mono text-slate-600 font-semibold text-[10px]">{{ percentUsed }}%</span>
          </div>

          <div class="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
            <div
              class="h-full rounded-full transition-all duration-300"
              :class="percentUsed > 85 ? 'bg-rose-500' : 'bg-blue-600'"
              :style="{ width: `${percentUsed}%` }"
            ></div>
          </div>

          <div class="flex items-center justify-between text-[10px] text-slate-500">
            <span>{{ storageUsedMB }} MB of {{ storageLimitGB }} GB</span>
            <router-link to="/app/billing" class="text-blue-600 font-medium hover:underline">
              Upgrade
            </router-link>
          </div>
        </div>

        <!-- Master Administrator Card: Shown for Super Admin (no user pack) -->
        <div v-else class="p-3 rounded-xl bg-indigo-50/70 border border-indigo-200/80 shadow-2xs space-y-2 text-xs">
          <div class="flex items-center justify-between">
            <span class="font-bold text-indigo-900 flex items-center space-x-1.5">
              <ShieldAlert class="w-3.5 h-3.5 text-indigo-600" />
              <span>Platform Administrator</span>
            </span>
            <span class="text-[9px] bg-indigo-600 text-white px-1.5 py-0.5 rounded font-mono font-bold">Admin</span>
          </div>
          <p class="text-[10px] text-slate-500 leading-snug">
            Platform manager • 100% pool capacity allocated to users.
          </p>
          <router-link
            to="/app/admin"
            class="inline-flex items-center space-x-1 text-[11px] text-indigo-700 font-semibold hover:text-indigo-900 pt-0.5"
          >
            <span>Open Admin Dashboard</span>
            <ArrowRight class="w-3 h-3" />
          </router-link>
        </div>

        <!-- User Profile Row -->
        <div class="flex items-center justify-between pt-0.5">
          <div class="flex items-center space-x-2.5 min-w-0">
            <div class="w-7 h-7 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-xs shrink-0 border border-blue-200">
              {{ (authStore.user?.full_name || authStore.user?.email || 'U')[0].toUpperCase() }}
            </div>
            <div class="min-w-0">
              <div class="text-xs font-semibold text-slate-900 truncate">
                {{ authStore.user?.full_name || 'My Vault' }}
              </div>
              <div class="text-[10px] text-slate-500 truncate">
                {{ authStore.user?.email }}
              </div>
            </div>
          </div>

          <button
            @click="handleLogout"
            class="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
            title="Sign out"
          >
            <LogOut class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </aside>

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden bg-slate-50">
      <!-- Unpaid Warning Banner -->
      <div
        v-if="!authStore.hasActiveSubscription"
        class="px-6 py-2.5 bg-amber-50 border-b border-amber-200 flex items-center justify-between text-xs text-amber-900"
      >
        <div class="flex items-center space-x-2">
          <AlertTriangle class="w-4 h-4 text-amber-600 shrink-0" />
          <span><strong>Subscription Required:</strong> Activate a monthly or yearly plan via Razorpay to unlock your cloud storage.</span>
        </div>
        <router-link
          to="/app/billing"
          class="px-3 py-1 rounded-lg bg-amber-600 text-white font-semibold hover:bg-amber-700 transition-colors shrink-0 shadow-xs"
        >
          Subscribe Now →
        </router-link>
      </div>

      <!-- Top Header -->
      <header class="h-14 border-b border-slate-200 bg-white/80 backdrop-blur-md flex items-center justify-between px-6 shrink-0 shadow-2xs">
        <!-- Breadcrumbs -->
        <div class="flex items-center space-x-2 text-xs font-medium text-slate-500">
          <template v-for="(crumb, idx) in filesStore.breadcrumbs" :key="crumb.id || idx">
            <button
              @click="filesStore.navigateUp(idx)"
              class="hover:text-slate-900 transition-colors"
              :class="{ 'text-slate-900 font-semibold': idx === filesStore.breadcrumbs.length - 1 }"
            >
              {{ crumb.name }}
            </button>
            <ChevronRight v-if="idx < filesStore.breadcrumbs.length - 1" class="w-3.5 h-3.5 text-slate-400" />
          </template>
        </div>

        <!-- Search & Status -->
        <div class="flex items-center space-x-3">
          <!-- Client-side decrypted search input -->
          <div class="relative w-64">
            <Search class="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              v-model="searchInput"
              @input="onSearch"
              placeholder="Search decrypted vault..."
              class="w-full pl-8 pr-3 py-1.5 rounded-xl bg-slate-100/70 border border-slate-200 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all"
            />
          </div>

          <!-- Subscription Badge -->
          <div
            class="px-2.5 py-1 rounded-lg text-[10px] font-medium tracking-wide flex items-center space-x-1"
            :class="authStore.hasActiveSubscription ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-700 border border-amber-200'"
          >
            <span class="w-1.5 h-1.5 rounded-full" :class="authStore.hasActiveSubscription ? 'bg-emerald-500' : 'bg-amber-500'"></span>
            <span>{{ authStore.hasActiveSubscription ? (authStore.user?.subscription?.plan_name || 'Active Plan') : 'Unpaid' }}</span>
          </div>
        </div>
      </header>

      <!-- Routed Page Container -->
      <main class="flex-1 overflow-y-auto p-6 bg-slate-50">
        <router-view />
      </main>

      <!-- Floating Upload Tray -->
      <UploadTray />
    </div>
  </div>
</template>
