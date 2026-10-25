<script setup lang="ts">
import { computed, onMounted, onUnmounted, provide, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { DialogRoot, DialogPortal, DialogOverlay, DialogContent, DialogTitle } from "reka-ui";
import AppSidebar from "./AppSidebar.vue";
import AppHeader from "./AppHeader.vue";
import UiBanner from "../components/ui/UiBanner.vue";
import UiButton from "../components/ui/UiButton.vue";
import UiSkeleton from "../components/ui/UiSkeleton.vue";
import CommandPalette from "../components/CommandPalette.vue";
import ShortcutsDialog from "../components/ShortcutsDialog.vue";
import VaultUnlockModal from "../features/auth/VaultUnlockModal.vue";
import ConflictDialog from "../features/files/ConflictDialog.vue";
import { useAuthStore } from "../stores/auth";
import { useFilesStore } from "../stores/files";
import { useUploadStore } from "../stores/upload";
import { useMediaQuery } from "../composables/useMediaQuery";
import { useShortcuts } from "../composables/useShortcuts";
import { useUploader } from "../composables/useUploader";
import { emitAppEvent, onAppEvent } from "../lib/events";
import { confirmDialog } from "../lib/confirm";
import { formatDate } from "../lib/format";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const filesStore = useFilesStore();
const uploadStore = useUploadStore();
const uploader = useUploader();

// ≥1280 full sidebar (collapsible), 768–1279 icon rail, <768 drawer.
const isDesktop = useMediaQuery("(min-width: 1280px)");
const isTablet = useMediaQuery("(min-width: 768px)");
const COLLAPSE_KEY = "sc_sidebar_collapsed";
const userCollapsed = ref(readCollapsed());
function readCollapsed() {
  try {
    return localStorage.getItem(COLLAPSE_KEY) === "1";
  } catch {
    return false;
  }
}
const collapsed = computed(() => (isDesktop.value ? userCollapsed.value : true));
function toggleCollapsed() {
  userCollapsed.value = !userCollapsed.value;
  try {
    localStorage.setItem(COLLAPSE_KEY, userCollapsed.value ? "1" : "0");
  } catch {}
}
const drawerOpen = ref(false);
watch(() => route.fullPath, () => (drawerOpen.value = false));

// Scroll container for virtualised lists.
const scrollEl = ref<HTMLElement | null>(null);
provide("scrollContainer", scrollEl);

// --- Plan banners --------------------------------------------------------------
const sub = computed(() => authStore.user?.subscription);
const isCustomer = computed(() => !authStore.isMasterAdmin);
const NO_PLAN_KEY = "sc_noplan_banner_dismissed";
const noPlanDismissed = ref(sessionStorage.getItem(NO_PLAN_KEY) === "1");
function dismissNoPlan() {
  noPlanDismissed.value = true;
  try {
    sessionStorage.setItem(NO_PLAN_KEY, "1");
  } catch {}
}
const banner = computed(() => {
  if (!isCustomer.value || !sub.value) return null;
  const s = sub.value;
  if (s.plan_code && !s.can_upload) {
    return { tone: "warning" as const, text: `Your plan has ended, so uploads are paused. Your files are kept until ${formatDate(s.grace_period_ends_at)}.`, cta: "Renew plan", dismissible: false, plan: s.plan_code };
  }
  if (!s.has_active_subscription) {
    return noPlanDismissed.value ? null : { tone: "info" as const, text: "You don't have a plan yet.", cta: "Choose a plan", dismissible: true, plan: undefined };
  }
  const days = s.days_until_expiration;
  if (typeof days === "number" && days >= 0 && days <= 7) {
    return { tone: "warning" as const, text: `Your plan ends on ${formatDate(s.current_period_end, { year: undefined })}. Extend now to keep uploading.`, cta: "Extend plan", dismissible: false, plan: s.plan_code ?? undefined };
  }
  return null;
});

// --- Vault ----------------------------------------------------------------------
const restoringGoogle = ref(false);
const needsUnlock = computed(() => isCustomer.value && !authStore.isVaultUnlocked && authStore.hasPasswordVault && route.meta.customer === true);

// --- Uploads, shortcuts and sign out ------------------------------------------
const fileInput = ref<HTMLInputElement | null>(null);
const folderInput = ref<HTMLInputElement | null>(null);
function onPicked(e: Event) {
  const input = e.target as HTMLInputElement;
  if (input.files?.length) void uploader.upload(Array.from(input.files), route.path.startsWith("/app/files") ? filesStore.currentParentId : null);
  input.value = "";
}

const offs: (() => void)[] = [];
onMounted(async () => {
  offs.push(
    onAppEvent("upload-files", () => uploader.ensureCanUpload() && fileInput.value?.click()),
    onAppEvent("upload-folder", () => uploader.ensureCanUpload() && folderInput.value?.click()),
    onAppEvent("new-folder", () => {
      if (!route.path.startsWith("/app/files")) router.push("/app/files");
    }),
    // "Choose a plan" prompts (upload limits, banners) open the plans page, or checkout directly
    // when the plan is already known (e.g. "Renew" on the expiry banner).
    onAppEvent("plan-picker", (payload) => {
      if (payload?.planCode) void router.push({ name: "checkout", query: { plan: payload.planCode } });
      else void router.push({ name: "plans", query: payload?.reason ? { reason: payload.reason } : {} });
    })
  );
  if (isCustomer.value && !authStore.isVaultUnlocked && authStore.user?.has_google && !authStore.hasPasswordVault) {
    restoringGoogle.value = true;
    await authStore.restoreGoogleVault();
    restoringGoogle.value = false;
  }
  authStore.fetchProfile().catch(() => {});
});
onUnmounted(() => offs.forEach((off) => off()));

useShortcuts(() => [
  { keys: "mod+k", allowInInputs: true, handler: () => emitAppEvent("command-palette") },
  { keys: "/", handler: () => emitAppEvent("command-palette") },
  { keys: "shift+?", handler: () => emitAppEvent("shortcuts-help") },
  { keys: "?", handler: () => emitAppEvent("shortcuts-help") },
  ...(isCustomer.value
    ? [
        { keys: "u", handler: () => emitAppEvent("upload-files") },
        { keys: "n", handler: () => emitAppEvent("new-folder") },
      ]
    : []),
]);

async function signOut() {
  const running = uploadStore.activeCount;
  if (running) {
    const ok = await confirmDialog({
      title: "Uploads are still running",
      body: `Signing out cancels ${running} ${running === 1 ? "upload" : "uploads"} in progress.`,
      confirmLabel: "Sign out and cancel uploads",
      danger: true,
    });
    if (!ok) return;
    uploadStore.cancelAll();
  }
  await authStore.logout();
  filesStore.reset();
  router.push("/login");
}
</script>

<template>
  <div class="flex h-[100dvh] overflow-hidden bg-canvas">
    <a
      href="#main-content"
      class="fixed left-3 top-3 z-[70] -translate-y-24 rounded bg-surface px-3 py-2 text-base font-medium text-fg shadow-md transition-transform focus:translate-y-0"
    >Skip to content</a>
    <input ref="fileInput" type="file" multiple class="hidden" tabindex="-1" aria-hidden="true" @change="onPicked" />
    <input ref="folderInput" type="file" webkitdirectory class="hidden" tabindex="-1" aria-hidden="true" @change="onPicked" />

    <aside
      v-if="isTablet"
      class="shrink-0 border-r border-line transition-[width] duration-slow ease-out"
      :class="collapsed ? 'w-16' : 'w-[248px]'"
      aria-label="Sidebar"
    >
      <AppSidebar :collapsed="collapsed" :collapsible="isDesktop" @toggle="toggleCollapsed" />
    </aside>
    <DialogRoot v-else v-model:open="drawerOpen">
      <DialogPortal>
        <DialogOverlay class="fixed inset-0 z-50 bg-overlay/40 data-[state=open]:animate-fade-in" />
        <DialogContent class="fixed inset-y-0 left-0 z-50 w-[280px] max-w-[85vw] border-r border-line shadow-xl focus:outline-none data-[state=open]:animate-slide-in-left">
          <DialogTitle class="sr-only">Navigation</DialogTitle>
          <AppSidebar :collapsed="false" :collapsible="false" @navigate="drawerOpen = false" />
        </DialogContent>
      </DialogPortal>
    </DialogRoot>

    <div class="flex min-w-0 flex-1 flex-col">
      <AppHeader :show-menu-button="!isTablet" @open-nav="drawerOpen = true" @sign-out="signOut" />
      <UiBanner
        v-if="banner"
        :tone="banner.tone"
        :dismissible="banner.dismissible"
        @dismiss="dismissNoPlan"
      >
        {{ banner.text }}
        <template #action>
          <UiButton variant="link" size="sm" class="font-semibold" @click="emitAppEvent('plan-picker', { planCode: banner.plan })">{{ banner.cta }}</UiButton>
        </template>
      </UiBanner>

      <main id="main-content" ref="scrollEl" class="min-h-0 flex-1 overflow-y-auto scrollbar-thin focus:outline-none" tabindex="-1">
        <div class="w-full px-4 pb-16 pt-4 sm:px-6 sm:pt-5">
          <div v-if="restoringGoogle" class="space-y-3" aria-busy="true">
            <UiSkeleton class="h-8 w-48" />
            <UiSkeleton class="h-11 w-full" />
            <UiSkeleton class="h-11 w-full" />
          </div>
          <router-view v-else />
        </div>
      </main>
    </div>

    <CommandPalette @sign-out="signOut" />
    <ShortcutsDialog />
    <VaultUnlockModal :open="needsUnlock" @sign-out="signOut" />
    <ConflictDialog />
  </div>
</template>
