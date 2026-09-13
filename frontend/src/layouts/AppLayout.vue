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
  Loader2,
} from "lucide-vue-next";

const router = useRouter();
const authStore = useAuthStore();
const filesStore = useFilesStore();
const uploadStore = useUploadStore();

const searchInput = ref("");
const fileInputRef = ref<HTMLInputElement | null>(null);

const unlockPassword = ref("");
const isUnlocking = ref(false);
const unlockError = ref("");

async function handleUnlockVault() {
  if (!unlockPassword.value) return;
  isUnlocking.value = true;
  unlockError.value = "";
  try {
    await authStore.unlockVault(unlockPassword.value);
    unlockPassword.value = "";
    if (authStore.hasActiveSubscription) {
      filesStore.fetchNodes();
    }
  } catch (err: any) {
    unlockError.value = err.message || "Failed to unlock vault. Please verify your password.";
  } finally {
    isUnlocking.value = false;
  }
}

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

        <!-- Quick Upload Action (Customer Accounts Only) -->
        <div v-if="!authStore.isMasterAdmin">
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
          <!-- Customer Navigation: Encrypted Vault, Shared Links, Billing -->
          <template v-if="!authStore.isMasterAdmin">
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
          </template>

          <!-- Master Admin Navigation: Platform Governance Only -->
          <template v-else>
            <router-link
              to="/app/admin"
              class="flex items-center space-x-3 px-3 py-2 rounded-xl transition-all border border-indigo-200/70"
              :class="$route.path.startsWith('/app/admin') ? 'bg-indigo-50 text-indigo-800 font-bold shadow-xs' : 'bg-indigo-50/40 text-indigo-700 hover:bg-indigo-100/60'"
            >
              <ShieldAlert class="w-4 h-4 text-indigo-600 shrink-0" />
              <div class="flex items-center justify-between w-full min-w-0">
                <span class="truncate">Admin Dashboard</span>
                <span class="text-[9px] bg-indigo-600 text-white px-1.5 py-0.5 rounded font-mono font-bold uppercase tracking-wider">Master</span>
              </div>
            </router-link>
          </template>

          <!-- Security & Sessions (Common) -->
          <router-link
            to="/app/settings"
            class="flex items-center space-x-3 px-3 py-2 rounded-xl transition-all"
            :class="$route.path === '/app/settings' ? 'bg-blue-50 text-blue-700 font-semibold' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70'"
          >
            <Settings class="w-4 h-4" :class="$route.path === '/app/settings' ? 'text-blue-600' : 'text-slate-400'" />
            <span>Security & Sessions</span>
          </router-link>
        </nav>
      </div>

      <!-- Storage Meter & Profile Footer -->
      <div class="p-4 border-t border-slate-200 space-y-3 bg-slate-50/50">
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
        <div v-else class="p-3 rounded-xl bg-indigo-50/70 border border-indigo-200/80 shadow-2xs space-y-1.5 text-xs">
          <div class="flex items-center justify-between">
            <span class="font-bold text-indigo-900 flex items-center space-x-1.5">
              <ShieldAlert class="w-3.5 h-3.5 text-indigo-600" />
              <span>Platform Administrator</span>
            </span>
            <span class="text-[9px] bg-indigo-600 text-white px-1.5 py-0.5 rounded font-mono font-bold">Admin</span>
          </div>
          <p class="text-[10px] text-slate-500 leading-snug">
            Platform governance & upstream storage pool supervisor.
          </p>
        </div>

        <!-- User Profile & Highlighted Sign Out Action -->
        <div class="pt-1 space-y-2">
          <div class="flex items-center space-x-2.5 min-w-0">
            <div class="w-7 h-7 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-xs shrink-0 border border-blue-200">
              {{ (authStore.user?.full_name || authStore.user?.email || 'U')[0].toUpperCase() }}
            </div>
            <div class="min-w-0 flex-1">
              <div class="text-xs font-semibold text-slate-900 truncate">
                {{ authStore.user?.full_name || (authStore.isMasterAdmin ? 'Master Administrator' : 'My Vault') }}
              </div>
              <div class="text-[10px] text-slate-500 truncate">
                {{ authStore.user?.email }}
              </div>
            </div>
          </div>

          <!-- Specifically Highlighted Logout Button in Sidebar -->
          <button
            @click="handleLogout"
            class="w-full flex items-center justify-center space-x-2 py-2 px-3 rounded-xl text-xs font-bold text-rose-700 bg-rose-50 hover:bg-rose-100 hover:text-rose-800 border border-rose-200 transition-all shadow-xs group cursor-pointer"
            title="Sign out of your account"
          >
            <LogOut class="w-4 h-4 text-rose-600 group-hover:scale-110 transition-transform" />
            <span>Sign Out</span>
          </button>
        </div>
      </div>
    </aside>

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden bg-slate-50">
      <!-- 90-Day Retention Grace Period Warning Banner -->
      <div
        v-if="!authStore.isMasterAdmin && authStore.user?.subscription && (authStore.user?.subscription?.is_in_grace_period || authStore.user?.subscription?.status === 'expired')"
        class="px-6 py-2.5 bg-amber-50 border-b border-amber-200 flex items-center justify-between text-xs text-amber-900"
      >
        <div class="flex items-center space-x-2.5">
          <AlertTriangle class="w-4 h-4 text-amber-600 shrink-0" />
          <span>
            <strong>Subscription Expired:</strong> Your encrypted vault files are preserved for 90 days
            <strong class="text-amber-800 underline">({{ authStore.user.subscription.retention_days_remaining || 90 }} days remaining before permanent deletion)</strong>.
            Uploads are currently locked. Renew your plan to secure your vault and resume uploads.
          </span>
        </div>
        <router-link
          to="/app/billing"
          class="px-3.5 py-1.5 rounded-xl bg-amber-600 hover:bg-amber-700 text-white font-semibold transition-colors shrink-0 shadow-xs text-xs"
        >
          Renew Subscription →
        </router-link>
      </div>

      <!-- General Unpaid Warning Banner (For newly registered users with no active plan) -->
      <div
        v-else-if="!authStore.hasActiveSubscription && !authStore.isMasterAdmin"
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
        <!-- Breadcrumbs or Admin Title -->
        <div class="flex items-center space-x-2 text-xs font-medium text-slate-500">
          <template v-if="!authStore.isMasterAdmin">
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
          </template>
          <template v-else>
            <div class="flex items-center space-x-2 text-slate-800 font-bold">
              <ShieldAlert class="w-4 h-4 text-indigo-600" />
              <span>Platform Management Console</span>
            </div>
          </template>
        </div>

        <!-- Search, Status & Prominent Top Sign Out -->
        <div class="flex items-center space-x-3">
          <!-- Client-side decrypted search input (Customers Only) -->
          <div v-if="!authStore.isMasterAdmin" class="relative w-64">
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

          <!-- Specifically Highlighted Top-Right Sign Out Button -->
          <button
            @click="handleLogout"
            class="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-bold text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 transition-all shadow-xs cursor-pointer"
            title="Sign Out"
          >
            <LogOut class="w-3.5 h-3.5 text-rose-600" />
            <span>Sign Out</span>
          </button>
        </div>
      </header>

      <!-- Routed Page Container -->
      <main class="flex-1 overflow-y-auto p-6 bg-slate-50">
        <router-view />
      </main>
    </div>

    <!-- Unlock Vault Modal (when user session is valid but client-side masterKey is locked) -->
    <div
      v-if="!authStore.isVaultUnlocked && !authStore.isMasterAdmin && ($route.path.startsWith('/app/files') || $route.path.startsWith('/app/shared'))"
      class="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4"
    >
      <div class="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-5">
        <div class="flex items-center space-x-3">
          <div class="w-10 h-10 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 shrink-0">
            <Lock class="w-5 h-5" />
          </div>
          <div>
            <h3 class="text-base font-bold text-slate-900">Unlock Encrypted Vault</h3>
            <p class="text-xs text-slate-500">Enter your master password to decrypt your zero-knowledge storage</p>
          </div>
        </div>

        <div v-if="unlockError" class="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-start space-x-2">
          <AlertTriangle class="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <span>{{ unlockError }}</span>
        </div>

        <form @submit.prevent="handleUnlockVault" class="space-y-4">
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Master Password</label>
            <input
              type="password"
              v-model="unlockPassword"
              required
              autofocus
              placeholder="Enter your password"
              class="w-full px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-200 text-slate-900 text-xs placeholder:text-slate-400 focus:bg-white focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all"
            />
          </div>

          <div class="flex items-center justify-between pt-2">
            <button
              type="button"
              @click="handleLogout"
              class="text-xs text-slate-500 hover:text-slate-800 font-medium"
            >
              Sign out instead
            </button>
            <button
              type="submit"
              :disabled="isUnlocking"
              class="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold flex items-center space-x-2 disabled:opacity-50 transition-colors shadow-sm shadow-blue-500/20"
            >
              <Loader2 v-if="isUnlocking" class="w-3.5 h-3.5 animate-spin" />
              <span>{{ isUnlocking ? 'Decrypting Vault...' : 'Unlock Vault' }}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
