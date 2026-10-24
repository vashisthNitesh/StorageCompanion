<script setup lang="ts">
import { onMounted, ref, type Component } from "vue";
import {
  LogIn,
  LogOut,
  KeyRound,
  ShieldCheck,
  ShieldOff,
  CreditCard,
  Upload,
  Download,
  Trash2,
  RotateCcw,
  FolderPlus,
  Pencil,
  UserPlus,
  Activity,
  MonitorX,
  Eye,
} from "lucide-vue-next";
import UiCard from "../../components/ui/UiCard.vue";
import UiButton from "../../components/ui/UiButton.vue";
import UiSkeleton from "../../components/ui/UiSkeleton.vue";
import UiAlert from "../../components/ui/UiAlert.vue";
import UiTooltip from "../../components/ui/UiTooltip.vue";
import { apiRequest } from "../../lib/api";
import { normalizeApiError } from "../../lib/errors";
import { formatDateTime, formatRelative } from "../../lib/format";

interface Entry {
  id: string;
  action: string;
  ip: string | null;
  created_at: string;
}

const EVENTS: Record<string, { label: string; icon: Component; tone?: string }> = {
  "auth.login": { label: "Signed in", icon: LogIn },
  "auth.google_login": { label: "Signed in with Google", icon: LogIn },
  "auth.logout": { label: "Signed out", icon: LogOut },
  "user.registered": { label: "Account created", icon: UserPlus },
  "user.registered_google": { label: "Account created with Google", icon: UserPlus },
  "user.password_changed": { label: "Password changed", icon: KeyRound, tone: "text-warning" },
  "mfa.enabled": { label: "Two-step verification turned on", icon: ShieldCheck, tone: "text-success" },
  "mfa.disabled": { label: "Two-step verification turned off", icon: ShieldOff, tone: "text-warning" },
  "session.revoked": { label: "Signed out a device", icon: MonitorX },
  "subscription.activated": { label: "Plan purchased", icon: CreditCard, tone: "text-primary" },
  "subscription.canceled": { label: "Plan set not to renew", icon: CreditCard },
  "file.uploaded": { label: "Uploaded a file", icon: Upload },
  "file.downloaded": { label: "Downloaded a file", icon: Download },
  "file.previewed": { label: "Opened a file", icon: Eye },
  "node.trashed": { label: "Moved an item to trash", icon: Trash2 },
  "node.restored": { label: "Restored an item", icon: RotateCcw },
  "node.deleted_permanently": { label: "Deleted an item forever", icon: Trash2 },
  "node.updated": { label: "Renamed or moved an item", icon: Pencil },
  "folder.created": { label: "Created a folder", icon: FolderPlus },
  "vault.created": { label: "Encrypted vault created", icon: ShieldCheck },
};
const describe = (action: string) => EVENTS[action] ?? { label: "Account activity", icon: Activity };

const entries = ref<Entry[]>([]);
const next = ref<string | null>(null);
const loading = ref(true);
const loadingMore = ref(false);
const error = ref("");

async function fetchPage(url: string) {
  const data = await apiRequest<{ results: Entry[]; next: string | null }>(url);
  // Cursor links are absolute; keep only the path so requests stay same-origin.
  next.value = data.next ? new URL(data.next, window.location.origin).pathname + new URL(data.next, window.location.origin).search : null;
  return data.results;
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    entries.value = await fetchPage("/api/v1/audit-logs/?page_size=15");
  } catch (err) {
    error.value = normalizeApiError(err).message;
  } finally {
    loading.value = false;
  }
}

async function more() {
  if (!next.value) return;
  loadingMore.value = true;
  try {
    entries.value = [...entries.value, ...(await fetchPage(next.value))];
  } catch (err) {
    error.value = normalizeApiError(err).message;
  } finally {
    loadingMore.value = false;
  }
}

defineExpose({ load });
onMounted(load);
</script>

<template>
  <UiCard id="activity" class="scroll-mt-6" :icon="Activity" icon-tone="neutral" title="Recent activity" description="Sign-ins, security changes, uploads and purchases." :padded="false">
    <div class="px-5 pb-5 pt-4">
      <div v-if="loading" class="space-y-4" aria-busy="true">
        <div v-for="i in 4" :key="i" class="flex items-center gap-3"><UiSkeleton class="h-8 w-8 rounded-full" /><UiSkeleton class="h-3.5 w-48" /></div>
      </div>
      <UiAlert v-else-if="error">{{ error }} <template #action><UiButton size="sm" @click="load">Retry</UiButton></template></UiAlert>
      <p v-else-if="!entries.length" class="text-base text-fg-muted">No activity yet.</p>
      <ol v-else class="relative space-y-4 before:absolute before:bottom-2 before:left-4 before:top-2 before:w-px before:bg-line">
        <li v-for="e in entries" :key="e.id" class="relative flex items-start gap-3">
          <span class="relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-line bg-surface" :class="describe(e.action).tone ?? 'text-fg-muted'">
            <component :is="describe(e.action).icon" :size="15" :stroke-width="1.75" aria-hidden="true" />
          </span>
          <div class="min-w-0 pt-1">
            <p class="text-base text-fg">{{ describe(e.action).label }}</p>
            <p class="tabular text-sm text-fg-subtle">
              <UiTooltip :content="formatDateTime(e.created_at)"><span>{{ formatRelative(e.created_at) }}</span></UiTooltip>
              <template v-if="e.ip"> · {{ e.ip }}</template>
            </p>
          </div>
        </li>
      </ol>
      <UiButton v-if="next && !loading" class="mt-5" size="sm" :loading="loadingMore" @click="more">Show more</UiButton>
    </div>
  </UiCard>
</template>
