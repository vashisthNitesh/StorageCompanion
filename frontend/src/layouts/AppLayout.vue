<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import {
  Folder,
  Trash2,
  CreditCard,
  Settings,
  LogOut,
  Menu,
  X,
  Search,
  Upload,
  FolderUp,
  ShieldCheck,
  AlertTriangle,
  Lock,
  Loader2,
  ChevronDown,
  Info,
} from "lucide-vue-next";
import AppLogo from "../components/AppLogo.vue";
import BaseModal from "../components/BaseModal.vue";
import PasswordInput from "../features/auth/PasswordInput.vue";
import { useAuthStore } from "../stores/auth";
import { useFilesStore } from "../stores/files";
import { useUploadStore } from "../stores/upload";
import { provideFilePicker } from "../composables/useFilePicker";
import { formatBytes, formatDate } from "../lib/format";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const filesStore = useFilesStore();
const uploadStore = useUploadStore();

const mobileNavOpen = ref(false);
const userMenuOpen = ref(false);
const mobileSearchOpen = ref(false);
const searchText = ref(filesStore.searchQuery);

const fileInput = ref<HTMLInputElement | null>(null);
const folderInput = ref<HTMLInputElement | null>(null);

const isCustomer = computed(() => !authStore.isMasterAdmin);
const sub = computed(() => authStore.user?.subscription);
const quota = computed(() => authStore.user?.quota);
const percentUsed = computed(() => Math.min(100, quota.value?.percent_used || 0));
const percentLabel = computed(() => {
  if (!quota.value?.bytes_used) return "0%";
  if (percentUsed.value < 1) return "<1%";
  return `${Math.round(percentUsed.value)}%`;
});

const nav = computed(() =>
  isCustomer.value
    ? [
        { to: "/app/files", label: "My files", icon: Folder },
        { to: "/app/trash", label: "Trash", icon: Trash2 },
        { to: "/app/billing", label: "Plan & billing", icon: CreditCard },
        { to: "/app/settings", label: "Security", icon: Settings },
      ]
    : [
        { to: "/app/admin", label: "Admin console", icon: ShieldCheck },
        { to: "/app/settings", label: "Security", icon: Settings },
      ]
);

const notice = computed(() => {
  if (!isCustomer.value || !sub.value) return null;
  const s = sub.value;
  if (s.is_in_grace_period || s.status === "expired" || s.status === "canceled") {
    const days = s.retention_days_remaining ?? 0;
    return {
      tone: "warning" as const,
      text: `Your plan has ended, so uploads are paused. Your files are kept until ${formatDate(s.grace_period_ends_at)}${days ? ` (${days} days)` : ""}. Renew to keep them.`,
      cta: "Renew plan",
    };
  }
  if (!s.has_active_subscription) {
    return { tone: "info" as const, text: "You don't have a plan yet. Choose one to start uploading files.", cta: "See plans" };
  }
  if (s.can_upload && typeof s.days_until_expiration === "number" && s.days_until_expiration <= 7 && s.days_until_expiration >= 0) {
    return {
      tone: "info" as const,
      text: `Your plan renews or ends on ${formatDate(s.current_period_end)}.`,
      cta: "Manage plan",
    };
  }
  return null;
});

// --- Uploads -----------------------------------------------------------------

function requirePlan(): boolean {
  if (authStore.canUpload) return true;
  router.push("/app/billing");
  return false;
}

const picker = {
  pickFiles: () => requirePlan() && fileInput.value?.click(),
  pickFolder: () => requirePlan() && folderInput.value?.click(),
};
provideFilePicker(picker);

function onPicked(e: Event) {
  const input = e.target as HTMLInputElement;
  if (input.files?.length) {
    void uploadStore.uploadFiles(input.files, route.path === "/app/files" ? filesStore.currentParentId : null);
  }
  input.value = "";
  mobileNavOpen.value = false;
}

// --- Search ------------------------------------------------------------------

let searchTimer: ReturnType<typeof setTimeout> | undefined;
watch(searchText, (q) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    if (q.trim() && route.path !== "/app/files") router.push("/app/files");
    void filesStore.search(q);
  }, 250);
});
watch(
  () => filesStore.searchQuery,
  (q) => {
    if (q !== searchText.value) searchText.value = q;
  }
);

// --- Vault unlock ------------------------------------------------------------

const unlockPassword = ref("");
const unlockError = ref("");
const unlocking = ref(false);
const restoringGoogle = ref(false);

const needsUnlock = computed(
  () => isCustomer.value && !authStore.isVaultUnlocked && authStore.hasPasswordVault && route.meta.customer === true
);

async function unlock() {
  unlocking.value = true;
  unlockError.value = "";
  try {
    await authStore.unlockVault(unlockPassword.value);
    unlockPassword.value = "";
  } catch (err: any) {
    unlockError.value = err.message;
  } finally {
    unlocking.value = false;
  }
}

async function logout() {
  userMenuOpen.value = false;
  await authStore.logout();
  filesStore.reset();
  router.push("/login");
}

function closeMenus(e: MouseEvent) {
  if (!(e.target as HTMLElement).closest("[data-user-menu]")) userMenuOpen.value = false;
}

watch(() => route.fullPath, () => {
  mobileNavOpen.value = false;
  userMenuOpen.value = false;
});

onMounted(async () => {
  document.addEventListener("click", closeMenus);
  if (isCustomer.value && !authStore.isVaultUnlocked && authStore.user?.has_google && !authStore.hasPasswordVault) {
    restoringGoogle.value = true;
    await authStore.restoreGoogleVault();
    restoringGoogle.value = false;
  }
  authStore.fetchProfile().catch(() => {});
});
onUnmounted(() => document.removeEventListener("click", closeMenus));

const initials = computed(() => (authStore.user?.full_name || authStore.user?.email || "?").trim().charAt(0).toUpperCase());
</script>

<template>
  <div class="flex h-[100dvh] overflow-hidden bg-slate-50">
    <input ref="fileInput" type="file" multiple class="hidden" @change="onPicked" />
    <input ref="folderInput" type="file" webkitdirectory class="hidden" @change="onPicked" />

    <!-- Mobile nav backdrop -->
    <Transition enter-active-class="transition-opacity" enter-from-class="opacity-0" leave-active-class="transition-opacity" leave-to-class="opacity-0">
      <div v-if="mobileNavOpen" class="fixed inset-0 z-40 bg-slate-900/40 lg:hidden" @click="mobileNavOpen = false"></div>
    </Transition>

    <!-- Sidebar -->
    <aside
      class="fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-slate-200 bg-white transition-transform duration-200 lg:static lg:z-auto lg:w-64 lg:translate-x-0"
      :class="mobileNavOpen ? 'translate-x-0 shadow-pop' : '-translate-x-full'"
      aria-label="Main navigation"
    >
      <div class="flex h-16 items-center justify-between px-5">
        <router-link :to="isCustomer ? '/app/files' : '/app/admin'"><AppLogo /></router-link>
        <button class="icon-btn lg:hidden" aria-label="Close menu" @click="mobileNavOpen = false"><X class="h-5 w-5" /></button>
      </div>

      <div v-if="isCustomer" class="px-4 pb-2">
        <div class="grid grid-cols-[1fr_auto] overflow-hidden rounded-lg shadow-sm">
          <button class="btn-primary h-10 rounded-none justify-start" @click="picker.pickFiles()">
            <Upload class="h-4 w-4" /> Upload files
          </button>
          <button
            class="btn-primary h-10 w-10 rounded-none border-l border-brand-500 px-0"
            title="Upload a folder"
            aria-label="Upload a folder"
            @click="picker.pickFolder()"
          >
            <FolderUp class="h-4 w-4" />
          </button>
        </div>
      </div>

      <nav class="flex-1 space-y-0.5 overflow-y-auto px-3 py-3">
        <router-link
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors"
          :class="route.path.startsWith(item.to) ? 'bg-brand-50 text-brand-700' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'"
        >
          <component :is="item.icon" class="h-[18px] w-[18px]" />
          {{ item.label }}
        </router-link>
      </nav>

      <div v-if="isCustomer" class="border-t border-slate-200 p-4">
        <div class="flex items-center justify-between text-sm">
          <span class="font-medium text-slate-700">Storage</span>
          <span class="text-slate-500">{{ percentLabel }}</span>
        </div>
        <div class="mt-2 h-2 overflow-hidden rounded-full bg-slate-100" role="progressbar" :aria-valuenow="percentUsed" aria-valuemin="0" aria-valuemax="100">
          <div
            class="h-full rounded-full transition-all"
            :class="percentUsed > 90 ? 'bg-rose-500' : percentUsed > 75 ? 'bg-amber-500' : 'bg-brand-600'"
            :style="{ width: `${Math.max(percentUsed, quota?.bytes_used ? 1 : 0)}%` }"
          ></div>
        </div>
        <p class="mt-2 text-xs text-slate-500">
          <template v-if="quota?.bytes_limit">{{ formatBytes(quota.bytes_used) }} of {{ formatBytes(quota.bytes_limit, 0) }} used</template>
          <template v-else>No storage plan</template>
        </p>
        <router-link to="/app/billing" class="mt-3 btn-secondary btn-sm w-full">
          {{ sub?.has_active_subscription ? "Get more storage" : "Choose a plan" }}
        </router-link>
      </div>
    </aside>

    <!-- Main column -->
    <div class="flex min-w-0 flex-1 flex-col">
      <header class="flex h-16 shrink-0 items-center gap-2 border-b border-slate-200 bg-white px-3 sm:px-6">
        <button class="icon-btn lg:hidden" aria-label="Open menu" title="Menu" @click="mobileNavOpen = true">
          <Menu class="h-5 w-5" />
        </button>

        <div v-if="isCustomer" class="flex-1" :class="mobileSearchOpen ? 'block' : 'hidden sm:block'">
          <div class="relative max-w-xl">
          <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            v-model="searchText"
            type="search"
            class="input h-10 bg-slate-50 pl-9 pr-9"
            placeholder="Search all your files and folders"
            aria-label="Search files"
            :disabled="!authStore.isVaultUnlocked"
            @keydown.esc="searchText = ''"
          />
          <button
            v-if="searchText"
            class="absolute right-1.5 top-1/2 -translate-y-1/2 icon-btn h-7 w-7"
            aria-label="Clear search"
            @click="searchText = ''"
          >
            <X class="h-4 w-4" />
          </button>
          </div>
        </div>
        <div v-else class="flex-1"></div>

        <button
          v-if="isCustomer"
          class="icon-btn sm:hidden"
          :aria-label="mobileSearchOpen ? 'Close search' : 'Search'"
          @click="mobileSearchOpen = !mobileSearchOpen; if (!mobileSearchOpen) searchText = ''"
        >
          <X v-if="mobileSearchOpen" class="h-5 w-5" />
          <Search v-else class="h-5 w-5" />
        </button>

        <div class="relative" data-user-menu :class="{ 'hidden sm:block': mobileSearchOpen }">
          <button
            class="flex items-center gap-2 rounded-full py-1 pl-1 pr-2 hover:bg-slate-100"
            :aria-expanded="userMenuOpen"
            aria-label="Account menu"
            @click="userMenuOpen = !userMenuOpen"
          >
            <span class="flex h-8 w-8 items-center justify-center rounded-full bg-brand-600 text-sm font-semibold text-white">{{ initials }}</span>
            <ChevronDown class="hidden h-4 w-4 text-slate-500 sm:block" />
          </button>
          <div v-if="userMenuOpen" class="absolute right-0 top-12 z-30 w-64 rounded-xl border border-slate-200 bg-white p-1.5 shadow-pop">
            <div class="px-3 py-2">
              <p class="truncate text-sm font-medium text-slate-900">{{ authStore.user?.full_name || "Your account" }}</p>
              <p class="truncate text-xs text-slate-500">{{ authStore.user?.email }}</p>
              <p v-if="isCustomer" class="mt-1.5">
                <span :class="sub?.has_active_subscription ? 'badge-green' : 'badge-gray'">{{ sub?.plan_name || "No plan" }}</span>
              </p>
              <p v-else class="mt-1.5"><span class="badge-blue">Administrator</span></p>
            </div>
            <div class="my-1 h-px bg-slate-100"></div>
            <router-link to="/app/settings" class="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-100">
              <Settings class="h-4 w-4" /> Security settings
            </router-link>
            <button class="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-rose-600 hover:bg-rose-50" @click="logout">
              <LogOut class="h-4 w-4" /> Sign out
            </button>
          </div>
        </div>
      </header>

      <div
        v-if="notice"
        class="flex flex-col gap-2 border-b px-4 py-3 text-sm sm:flex-row sm:items-center sm:justify-between sm:px-6"
        :class="notice.tone === 'warning' ? 'border-amber-200 bg-amber-50 text-amber-900' : 'border-brand-100 bg-brand-50 text-brand-900'"
        role="status"
      >
        <p class="flex items-start gap-2">
          <AlertTriangle v-if="notice.tone === 'warning'" class="mt-0.5 h-4 w-4 shrink-0" />
          <Info v-else class="mt-0.5 h-4 w-4 shrink-0" />
          {{ notice.text }}
        </p>
        <router-link to="/app/billing" class="btn-secondary btn-sm self-start sm:self-auto">{{ notice.cta }}</router-link>
      </div>

      <main class="flex-1 overflow-y-auto">
        <div class="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div v-if="restoringGoogle" class="flex items-center gap-2 py-16 text-sm text-slate-500 justify-center">
            <Loader2 class="h-4 w-4 animate-spin" /> Opening your vault…
          </div>
          <router-view v-else />
        </div>
      </main>
    </div>

    <BaseModal :open="needsUnlock" title="Unlock your files" size="sm" :dismissible="false">
      <form class="space-y-4" @submit.prevent="unlock">
        <p class="flex gap-2 text-sm text-slate-600">
          <Lock class="mt-0.5 h-4 w-4 shrink-0 text-brand-600" />
          Your files are encrypted with your password. Enter it to open them on this device.
        </p>
        <div v-if="unlockError" class="alert-error">{{ unlockError }}</div>
        <div>
          <label for="unlock-password" class="label">Password</label>
          <PasswordInput id="unlock-password" v-model="unlockPassword" autocomplete="current-password" required />
        </div>
        <div class="flex items-center justify-between gap-3 pt-1">
          <button type="button" class="btn-ghost" @click="logout">Sign out</button>
          <button type="submit" class="btn-primary" :disabled="unlocking || !unlockPassword">
            <Loader2 v-if="unlocking" class="h-4 w-4 animate-spin" />
            {{ unlocking ? "Unlocking…" : "Unlock" }}
          </button>
        </div>
      </form>
    </BaseModal>
  </div>
</template>
