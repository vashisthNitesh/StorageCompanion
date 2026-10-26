<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Check, Copy, Link2, LockKeyhole, Eye, Download, Trash2, ShieldCheck, Plus } from "lucide-vue-next";
import UiModal from "../../components/ui/UiModal.vue";
import UiButton from "../../components/ui/UiButton.vue";
import UiSegmented from "../../components/ui/UiSegmented.vue";
import UiSwitch from "../../components/ui/UiSwitch.vue";
import UiInput from "../../components/ui/UiInput.vue";
import UiPasswordInput from "../../components/ui/UiPasswordInput.vue";
import UiRadioGroup from "../../components/ui/UiRadioGroup.vue";
import UiAlert from "../../components/ui/UiAlert.vue";
import UiBadge from "../../components/ui/UiBadge.vue";
import UiSkeleton from "../../components/ui/UiSkeleton.vue";
import { useAuthStore } from "../../stores/auth";
import type { FileNode } from "../../stores/files";
import { formatBytes, formatDate, formatRelative } from "../../lib/format";
import { normalizeApiError } from "../../lib/errors";
import { confirmDialog } from "../../lib/confirm";
import { toast } from "../../lib/toast";
import { kindInfo, kindOf } from "../files/fileTypes";
import { createShare, listShares, revokeShare, urlForLink, type ExpiryChoice, type ShareLink } from "./shareLinks";

// Share a file by link. Keys are made in the browser; the link's key lives after the # and
// never reaches our servers.
const open = defineModel<boolean>("open", { default: false });
const props = defineProps<{ node: FileNode | null }>();
const authStore = useAuthStore();

const EXPIRY: { value: ExpiryChoice; label: string }[] = [
  { value: "1h", label: "1 hour" },
  { value: "1d", label: "1 day" },
  { value: "7d", label: "7 days" },
  { value: "30d", label: "30 days" },
  { value: "never", label: "Never" },
];

const expiresIn = ref<ExpiryChoice>("7d");
const access = ref<"download" | "view">("download");
const usePassword = ref(false);
const password = ref("");
const useLimit = ref(false);
const limit = ref("10");
const creating = ref(false);
const error = ref("");

const newUrl = ref("");
const copiedId = ref<string | null>(null);
const links = ref<ShareLink[]>([]);
const loadingLinks = ref(false);
const showForm = ref(true);

const limitValue = computed(() => Math.floor(Number(limit.value)));
const limitInvalid = computed(() => useLimit.value && !(limitValue.value >= 1 && limitValue.value <= 10000));
const passwordInvalid = computed(() => usePassword.value && password.value.length < 4);

watch(
  () => [open.value, props.node?.id],
  async () => {
    if (!open.value || !props.node) return;
    newUrl.value = "";
    error.value = "";
    password.value = "";
    usePassword.value = false;
    useLimit.value = false;
    await loadLinks();
    showForm.value = links.value.length === 0;
  },
  { immediate: true }
);

async function loadLinks() {
  if (!props.node) return;
  loadingLinks.value = true;
  try {
    links.value = await listShares(props.node.id);
  } catch (err) {
    error.value = normalizeApiError(err).message;
  } finally {
    loadingLinks.value = false;
  }
}

async function create() {
  if (!props.node) return;
  if (!authStore.masterKey) {
    error.value = "Unlock your files first.";
    return;
  }
  if (passwordInvalid.value || limitInvalid.value) return;
  creating.value = true;
  error.value = "";
  try {
    const { link, url } = await createShare(props.node, authStore.masterKey, {
      expiresIn: expiresIn.value,
      password: usePassword.value ? password.value : undefined,
      maxDownloads: useLimit.value ? limitValue.value : null,
      allowDownload: access.value === "download",
    });
    newUrl.value = url;
    links.value = [link, ...links.value];
    showForm.value = false;
    password.value = "";
    void copy(url, link.id);
  } catch (err) {
    error.value = normalizeApiError(err).message;
  } finally {
    creating.value = false;
  }
}

async function copy(url: string, id: string) {
  try {
    await navigator.clipboard.writeText(url);
    copiedId.value = id;
    setTimeout(() => copiedId.value === id && (copiedId.value = null), 2000);
  } catch {
    toast.error("Couldn't copy. Select the link and copy it yourself.");
  }
}

async function copyExisting(link: ShareLink) {
  if (!authStore.masterKey) return toast.info("Unlock your files first.");
  try {
    await copy(await urlForLink(link, authStore.masterKey), link.id);
  } catch {
    toast.error("Couldn't rebuild this link. Create a new one.");
  }
}

async function revoke(link: ShareLink) {
  const ok = await confirmDialog({
    title: "Turn off this link?",
    body: "Anyone with the link loses access straight away, including downloads in progress. People who already downloaded the file keep their copy.",
    confirmLabel: "Turn off link",
    danger: true,
    action: () => revokeShare(link.id),
  });
  if (!ok) return;
  links.value = links.value.filter((l) => l.id !== link.id);
  if (!links.value.length) {
    newUrl.value = "";
    showForm.value = true;
  }
  toast.success("Link turned off");
}

function describe(link: ShareLink): string {
  const parts: string[] = [];
  if (link.status === "expired") parts.push(`Expired ${formatDate(link.expires_at)}`);
  else if (link.expires_at) parts.push(`Expires ${formatDate(link.expires_at, { hour: "numeric", minute: "2-digit" })}`);
  else parts.push("Never expires");
  parts.push(link.max_downloads ? `${link.download_count} of ${link.max_downloads} opens` : `${link.download_count} ${link.download_count === 1 ? "open" : "opens"}`);
  return parts.join(" · ");
}

const STATUS_BADGE: Partial<Record<ShareLink["status"], { label: string; tone: "warning" | "danger" | "neutral" }>> = {
  expired: { label: "Expired", tone: "neutral" },
  limit_reached: { label: "Limit reached", tone: "warning" },
  unavailable: { label: "File changed", tone: "warning" },
};
</script>

<template>
  <UiModal v-model:open="open" title="Share file" size="lg" :dismissible="!creating">
    <div v-if="node" class="space-y-5">
      <!-- File -->
      <div class="flex items-center gap-3 rounded-lg border border-line bg-canvas-subtle px-3 py-2.5">
        <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-md" :class="kindInfo(kindOf(node)).tint">
          <component :is="kindInfo(kindOf(node)).icon" :size="18" :stroke-width="1.75" aria-hidden="true" />
        </span>
        <div class="min-w-0">
          <p class="truncate text-base font-medium text-fg">{{ node.name }}</p>
          <p class="text-sm text-fg-subtle">{{ formatBytes(node.size_bytes) }}</p>
        </div>
      </div>

      <!-- New link -->
      <div v-if="newUrl" class="rounded-lg border border-primary/40 bg-primary-soft/60 p-4">
        <p class="flex items-center gap-2 text-base font-medium text-fg"><Link2 :size="16" class="text-primary" aria-hidden="true" />Link ready{{ copiedId ? " and copied" : "" }}</p>
        <div class="mt-3 flex flex-col gap-2 sm:flex-row">
          <UiInput :model-value="newUrl" readonly aria-label="Share link" class="font-mono text-sm" @focus="($event.target as HTMLInputElement).select()" />
          <UiButton variant="primary" class="shrink-0" :icon="copiedId === links[0]?.id ? Check : Copy" @click="copy(newUrl, links[0]!.id)">
            {{ copiedId === links[0]?.id ? "Copied" : "Copy link" }}
          </UiButton>
        </div>
        <p class="mt-2 text-sm text-fg-muted">
          Anyone with this link can open the file<template v-if="links[0]?.password_protected"> with the password</template>. Send the password separately.
        </p>
      </div>

      <!-- Settings -->
      <form v-if="showForm" class="space-y-4 rounded-lg border border-line p-4" novalidate @submit.prevent="create">
        <div>
          <p class="mb-2 text-sm font-medium text-fg">Link expires after</p>
          <div class="overflow-x-auto pb-0.5"><UiSegmented v-model="expiresIn" :options="EXPIRY" label="Link expires after" size="sm" /></div>
        </div>
        <div>
          <p class="mb-2 text-sm font-medium text-fg">People with the link can</p>
          <UiRadioGroup
            v-model="access"
            label="People with the link can"
            orientation="horizontal"
            :options="[
              { value: 'download', label: 'View and download' },
              { value: 'view', label: 'View only', description: 'No download button. Viewers can still save what they see.' },
            ]"
          />
        </div>
        <div class="space-y-2 border-t border-line pt-4">
          <UiSwitch v-model="usePassword" label="Require a password" description="Adds a second key that only people with the password have." />
          <UiPasswordInput v-if="usePassword" v-model="password" autocomplete="new-password" aria-label="Link password" :invalid="passwordInvalid && !!password" placeholder="At least 4 characters" />
        </div>
        <div class="space-y-2">
          <UiSwitch v-model="useLimit" label="Limit how many times it can be opened" />
          <div v-if="useLimit" class="flex items-center gap-2">
            <UiInput v-model="limit" type="number" inputmode="numeric" min="1" max="10000" class="w-28" aria-label="Open limit" :invalid="limitInvalid" />
            <span class="text-sm text-fg-muted">opens</span>
          </div>
        </div>
        <UiAlert v-if="error">{{ error }}</UiAlert>
        <div class="flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-between">
          <p class="flex items-center gap-1.5 text-sm text-fg-subtle"><ShieldCheck :size="15" class="text-success" aria-hidden="true" />Encrypted in your browser. We can't open shared files.</p>
          <UiButton type="submit" variant="primary" :icon="Link2" :loading="creating" :disabled="passwordInvalid || limitInvalid">Create link</UiButton>
        </div>
      </form>
      <UiButton v-else variant="secondary" :icon="Plus" @click="showForm = true; newUrl = ''">New link</UiButton>

      <!-- Active links -->
      <section v-if="loadingLinks || links.length" aria-labelledby="active-links">
        <h3 id="active-links" class="text-sm font-semibold text-fg">Active links <span class="font-normal text-fg-subtle">({{ links.length }})</span></h3>
        <div v-if="loadingLinks" class="mt-2 space-y-2"><UiSkeleton class="h-14 w-full" /></div>
        <ul v-else class="mt-2 divide-y divide-line rounded-lg border border-line">
          <li v-for="l in links" :key="l.id" class="flex flex-wrap items-center gap-3 px-3 py-2.5">
            <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-canvas-subtle text-fg-muted"><Link2 :size="16" aria-hidden="true" /></span>
            <div class="min-w-0 flex-1">
              <p class="flex flex-wrap items-center gap-1.5 text-sm font-medium text-fg">
                Created {{ formatRelative(l.created_at) }}
                <UiBadge v-if="l.password_protected" :icon="LockKeyhole">Password</UiBadge>
                <UiBadge v-if="!l.allow_download" :icon="Eye">View only</UiBadge>
                <UiBadge v-else :icon="Download">Download</UiBadge>
                <UiBadge v-if="STATUS_BADGE[l.status]" :tone="STATUS_BADGE[l.status]!.tone">{{ STATUS_BADGE[l.status]!.label }}</UiBadge>
              </p>
              <p class="text-xs text-fg-muted">{{ describe(l) }}</p>
            </div>
            <div class="flex shrink-0 gap-1">
              <UiButton v-if="l.status === 'active'" size="sm" variant="ghost" :icon="copiedId === l.id ? Check : Copy" @click="copyExisting(l)">{{ copiedId === l.id ? "Copied" : "Copy" }}</UiButton>
              <UiButton size="sm" variant="danger-ghost" :icon="Trash2" :aria-label="`Turn off link created ${formatRelative(l.created_at)}`" @click="revoke(l)">Revoke</UiButton>
            </div>
          </li>
        </ul>
      </section>
    </div>
  </UiModal>
</template>
