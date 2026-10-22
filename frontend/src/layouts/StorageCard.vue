<script setup lang="ts">
import { computed } from "vue";
import { HardDrive } from "lucide-vue-next";
import UiProgress from "../components/ui/UiProgress.vue";
import UiProgressCircle from "../components/ui/UiProgressCircle.vue";
import UiButton from "../components/ui/UiButton.vue";
import UiTooltip from "../components/ui/UiTooltip.vue";
import { useAuthStore } from "../stores/auth";
import { emitAppEvent } from "../lib/events";
import { formatBytes, formatDate } from "../lib/format";

defineProps<{ compact?: boolean }>();
const authStore = useAuthStore();
const sub = computed(() => authStore.user?.subscription);
const quota = computed(() => authStore.user?.quota);
const used = computed(() => quota.value?.bytes_used ?? 0);
const limit = computed(() => quota.value?.bytes_limit ?? 0);
const pct = computed(() => (limit.value ? Math.min(100, (used.value / limit.value) * 100) : 0));
const tone = computed(() => (pct.value >= 95 ? "danger" : pct.value >= 80 ? "warning" : "primary"));
const hasPlan = computed(() => !!sub.value?.has_active_subscription);
const ended = computed(() => !!sub.value?.plan_code && !sub.value?.can_upload);
const summary = computed(() => `${formatBytes(used.value)} of ${limit.value ? formatBytes(limit.value, 0) : "0 GB"} used`);
</script>

<template>
  <UiTooltip v-if="compact" :content="hasPlan ? summary : 'No plan yet'" side="right">
    <button
      type="button"
      class="mx-auto flex h-10 w-10 items-center justify-center rounded"
      :class="tone === 'danger' ? 'text-danger' : tone === 'warning' ? 'text-warning' : 'text-primary'"
      :aria-label="hasPlan ? `Storage: ${summary}` : 'Choose a plan'"
      @click="emitAppEvent('plan-picker', {})"
    >
      <UiProgressCircle v-if="hasPlan" :value="pct" :size="22" />
      <HardDrive v-else :size="20" :stroke-width="1.75" class="text-fg-subtle" />
    </button>
  </UiTooltip>

  <div v-else-if="!hasPlan && !ended" class="rounded-lg border border-line bg-surface p-3">
    <p class="text-sm font-medium text-fg">No plan yet</p>
    <p class="mt-0.5 text-sm text-fg-muted">Choose one to start uploading.</p>
    <UiButton class="mt-3" variant="primary" size="sm" block @click="emitAppEvent('plan-picker', {})">Choose a plan</UiButton>
  </div>

  <div v-else class="rounded-lg border border-line bg-surface p-3">
    <div class="flex items-baseline justify-between gap-2">
      <p class="text-sm font-medium text-fg">Storage</p>
      <p class="tabular text-xs text-fg-subtle">{{ pct < 1 && used ? "<1" : Math.round(pct) }}%</p>
    </div>
    <UiProgress class="mt-2" :value="pct" :tone="tone" size="sm" label="Storage used" />
    <p class="tabular mt-2 text-sm text-fg-muted">{{ summary }}</p>
    <p class="mt-1 text-xs text-fg-subtle">
      <template v-if="ended">Plan ended · files kept until {{ formatDate(sub?.grace_period_ends_at) }}</template>
      <template v-else>{{ sub?.plan_name }} · renews manually on {{ formatDate(sub?.current_period_end) }}</template>
    </p>
    <UiButton v-if="ended || pct >= 80" class="mt-3" :variant="ended ? 'primary' : 'secondary'" size="sm" block @click="emitAppEvent('plan-picker', {})">
      {{ ended ? "Renew plan" : "Get more storage" }}
    </UiButton>
  </div>
</template>
