<script setup lang="ts">
import { computed, ref } from "vue";
import { LifeBuoy, Check, AlertTriangle } from "lucide-vue-next";
import UiCard from "../../components/ui/UiCard.vue";
import UiButton from "../../components/ui/UiButton.vue";
import RecoveryKeyDialog from "../auth/RecoveryKeyDialog.vue";
import { useAuthStore } from "../../stores/auth";
import { formatDate } from "../../lib/format";

const authStore = useAuthStore();
const hasKey = computed(() => !!authStore.user?.has_recovery_key);
const open = ref(false);
defineExpose({ start: () => (open.value = true) });
</script>

<template>
  <UiCard id="recovery-key" class="scroll-mt-6" :icon="LifeBuoy" title="Recovery key" description="Lets you choose a new password without losing your files.">
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <p class="flex items-start gap-2 text-base" :class="hasKey ? 'text-fg-muted' : 'text-warning'">
        <Check v-if="hasKey" :size="18" class="mt-0.5 shrink-0 text-success" aria-hidden="true" />
        <AlertTriangle v-else :size="18" class="mt-0.5 shrink-0" aria-hidden="true" />
        <span v-if="hasKey">Saved {{ authStore.user?.recovery_key_confirmed_at ? `on ${formatDate(authStore.user.recovery_key_confirmed_at)}` : "" }}. Lost it? Create a new one; the old key stops working.</span>
        <span v-else>Not set up. If you forget your password, you'd lose access to your files.</span>
      </p>
      <UiButton class="shrink-0" :variant="hasKey ? 'secondary' : 'primary'" :disabled="!authStore.isVaultUnlocked" @click="open = true">
        {{ hasKey ? "Create new key" : "Create recovery key" }}
      </UiButton>
    </div>
    <p v-if="!authStore.isVaultUnlocked" class="mt-3 text-sm text-fg-subtle">Open My files and unlock your vault first.</p>
    <RecoveryKeyDialog v-model:open="open" :replacing="hasKey" />
  </UiCard>
</template>
