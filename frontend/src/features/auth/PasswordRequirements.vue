<script setup lang="ts">
import { computed } from "vue";
import { Check, X } from "lucide-vue-next";
import { passwordStrength } from "../settings/passwordStrength";

// Strength bar and requirement checklist for choosing a new password.
const props = defineProps<{ password: string }>();
const strength = computed(() => passwordStrength(props.password));
// "Different from your current password" doesn't apply here.
const checks = computed(() => strength.value.checks.filter((c) => !/current/.test(c.label)));
const barTone = computed(() => ["bg-danger", "bg-danger", "bg-warning", "bg-success", "bg-success"][strength.value.score]);
</script>

<template>
  <div class="space-y-3">
    <div v-if="password" class="flex items-center gap-3" aria-live="polite">
      <div class="flex flex-1 gap-1" aria-hidden="true">
        <span v-for="i in 4" :key="i" class="h-1.5 flex-1 rounded-full" :class="i <= strength.score ? barTone : 'bg-line'" />
      </div>
      <span class="text-sm font-medium text-fg-muted">{{ strength.label }}</span>
    </div>
    <ul class="space-y-1.5" aria-label="Password requirements">
      <li v-for="c in checks" :key="c.label" class="flex items-center gap-2 text-sm" :class="c.ok ? 'text-success' : 'text-fg-subtle'">
        <Check v-if="c.ok" :size="14" :stroke-width="2.5" aria-hidden="true" />
        <X v-else :size="14" :stroke-width="2.5" aria-hidden="true" />
        {{ c.label }}<span class="sr-only">{{ c.ok ? " (met)" : " (not met)" }}</span>
      </li>
    </ul>
  </div>
</template>
