<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { Laptop, Smartphone, LogOut, MonitorSmartphone } from "lucide-vue-next";
import UiCard from "../../components/ui/UiCard.vue";
import UiBadge from "../../components/ui/UiBadge.vue";
import UiButton from "../../components/ui/UiButton.vue";
import UiSkeleton from "../../components/ui/UiSkeleton.vue";
import UiAlert from "../../components/ui/UiAlert.vue";
import UiTooltip from "../../components/ui/UiTooltip.vue";
import { apiRequest } from "../../lib/api";
import { confirmDialog } from "../../lib/confirm";
import { normalizeApiError } from "../../lib/errors";
import { reportError } from "../../lib/reportError";
import { toast } from "../../lib/toast";
import { formatDateTime, formatRelative } from "../../lib/format";

interface SessionRow {
  id: string;
  device_label: string;
  ip_address: string | null;
  last_seen: string;
  created_at: string;
  is_current: boolean;
}

const sessions = ref<SessionRow[]>([]);
const loading = ref(true);
const error = ref("");
const busy = ref<string | null>(null);

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const list = await apiRequest<SessionRow[]>("/api/v1/auth/sessions");
    sessions.value = list.sort((a, b) => Number(b.is_current) - Number(a.is_current));
  } catch (err) {
    error.value = normalizeApiError(err).message;
  } finally {
    loading.value = false;
  }
}

async function revoke(s: SessionRow) {
  busy.value = s.id;
  try {
    await apiRequest(`/api/v1/auth/sessions/${s.id}`, { method: "DELETE" });
    sessions.value = sessions.value.filter((x) => x.id !== s.id);
    toast.success(`Signed out ${s.device_label}`);
  } catch (err) {
    reportError(err, { retry: () => void revoke(s) });
  } finally {
    busy.value = null;
  }
}

async function revokeOthers() {
  const others = sessions.value.filter((s) => !s.is_current);
  const ok = await confirmDialog({
    title: "Sign out all other devices?",
    body: `${others.length} ${others.length === 1 ? "device" : "devices"} will be signed out immediately.`,
    confirmLabel: "Sign out other devices",
    danger: true,
    action: async () => {
      for (const s of others) {
        await apiRequest(`/api/v1/auth/sessions/${s.id}`, { method: "DELETE" });
        sessions.value = sessions.value.filter((x) => x.id !== s.id);
      }
    },
  });
  if (ok) toast.success("Other devices were signed out.");
}

/** Long lists start collapsed; this device is always first. */
const COLLAPSED = 5;
const showAll = ref(false);
const visible = computed(() => (showAll.value ? sessions.value : sessions.value.slice(0, COLLAPSED)));
const isMobile = (label: string) => /iOS|Android/.test(label);
defineExpose({ load, sessions, loading });
onMounted(load);
</script>

<template>
  <UiCard id="devices" class="scroll-mt-6" :icon="MonitorSmartphone" title="Devices" description="Where your account is signed in right now." :padded="false">
    <template #actions>
      <UiButton v-if="sessions.some((s) => !s.is_current)" size="sm" :icon="LogOut" @click="revokeOthers">Sign out others</UiButton>
    </template>
    <div class="mt-4">
      <div v-if="loading" class="space-y-3 px-5 pb-5" aria-busy="true">
        <UiSkeleton v-for="i in 2" :key="i" class="h-12 w-full" />
      </div>
      <UiAlert v-else-if="error" class="mx-5 mb-5">
        {{ error }} <template #action><UiButton size="sm" @click="load">Retry</UiButton></template>
      </UiAlert>
      <ul v-else class="divide-y divide-line border-t border-line">
        <li v-for="s in visible" :key="s.id" class="flex items-center gap-4 px-5 py-3">
          <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-canvas-subtle text-fg-muted">
            <Smartphone v-if="isMobile(s.device_label)" :size="18" :stroke-width="1.75" aria-hidden="true" />
            <Laptop v-else :size="18" :stroke-width="1.75" aria-hidden="true" />
          </span>
          <div class="min-w-0 flex-1">
            <p class="flex flex-wrap items-center gap-2 text-base font-medium text-fg">
              {{ s.device_label }}
              <UiBadge v-if="s.is_current" tone="success">This device</UiBadge>
            </p>
            <p class="tabular truncate text-sm text-fg-subtle">
              {{ s.ip_address || "Unknown IP" }} ·
              <UiTooltip :content="formatDateTime(s.last_seen)"><span>active {{ formatRelative(s.last_seen) }}</span></UiTooltip>
            </p>
          </div>
          <UiButton v-if="!s.is_current" size="sm" variant="ghost" :loading="busy === s.id" @click="revoke(s)">Sign out</UiButton>
        </li>
      </ul>
      <div v-if="!loading && !error && sessions.length > COLLAPSED" class="border-t border-line px-5 py-2.5">
        <UiButton variant="ghost" size="sm" @click="showAll = !showAll">
          {{ showAll ? "Show fewer" : `Show all ${sessions.length} devices` }}
        </UiButton>
      </div>
    </div>
  </UiCard>
</template>
