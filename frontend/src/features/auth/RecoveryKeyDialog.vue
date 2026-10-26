<script setup lang="ts">
import { ref, watch } from "vue";
import { ShieldCheck } from "lucide-vue-next";
import UiModal from "../../components/ui/UiModal.vue";
import UiButton from "../../components/ui/UiButton.vue";
import UiAlert from "../../components/ui/UiAlert.vue";
import UiFormField from "../../components/ui/UiFormField.vue";
import UiPasswordInput from "../../components/ui/UiPasswordInput.vue";
import RecoveryKeyPanel from "./RecoveryKeyPanel.vue";
import { useAuthStore } from "../../stores/auth";
import { normalizeApiError } from "../../lib/errors";
import { toast } from "../../lib/toast";

// Creates (or replaces) the recovery key of an unlocked vault. A key made at sign-up that
// hasn't been confirmed yet is shown again instead of making a new one.
const open = defineModel<boolean>("open", { default: false });
const props = defineProps<{ replacing?: boolean }>();
const emit = defineEmits<{ later: [] }>();
const authStore = useAuthStore();

const stage = ref<"intro" | "show">("intro");
const key = ref("");
const saved = ref(false);
const password = ref("");
const needsPassword = ref(false);
const busy = ref(false);
const error = ref("");
let save: ((password?: string) => Promise<void>) | null = null;

watch(open, (v) => {
  if (!v) return;
  error.value = "";
  saved.value = false;
  password.value = "";
  if (authStore.pendingRecoveryKey && !props.replacing) {
    key.value = authStore.pendingRecoveryKey;
    save = () => authStore.confirmRecoveryKey();
    needsPassword.value = false;
    stage.value = "show";
  } else {
    stage.value = "intro";
  }
}, { immediate: true });

async function create() {
  busy.value = true;
  error.value = "";
  try {
    const prepared = await authStore.prepareRecoveryKey();
    key.value = prepared.display;
    save = prepared.save;
    needsPassword.value = authStore.recoveryNeedsPassword();
    stage.value = "show";
  } catch (err) {
    error.value = normalizeApiError(err).message;
  } finally {
    busy.value = false;
  }
}

async function finish() {
  if (!save) return;
  if (needsPassword.value && !password.value) {
    error.value = "Enter your password to save the new key.";
    return;
  }
  busy.value = true;
  error.value = "";
  try {
    await save(needsPassword.value ? password.value : undefined);
    toast.success("Recovery key saved");
    open.value = false;
  } catch (err) {
    const n = normalizeApiError(err);
    error.value = /password/i.test(n.message) ? "That password isn't right." : n.message;
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <UiModal v-model:open="open" :title="replacing ? 'Create a new recovery key' : 'Save your recovery key'" size="md" :dismissible="!busy">
    <div v-if="stage === 'intro'" class="space-y-4">
      <p class="flex gap-2.5 text-base text-fg-muted">
        <ShieldCheck :size="20" :stroke-width="1.75" class="mt-0.5 shrink-0 text-primary" aria-hidden="true" />
        <span>
          <template v-if="replacing">Your current recovery key will stop working. Make sure you save the new one.</template>
          <template v-else>
            Your password encrypts your files, so we can't reset it for you. A recovery key lets you choose a new password without losing them. It takes a
            minute.
          </template>
        </span>
      </p>
      <UiAlert v-if="error">{{ error }}</UiAlert>
      <div class="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <UiButton v-if="!replacing" variant="ghost" @click="emit('later'); open = false">Remind me later</UiButton>
        <UiButton variant="primary" :loading="busy" @click="create">Create recovery key</UiButton>
      </div>
    </div>
    <form v-else class="space-y-4" novalidate @submit.prevent="finish">
      <RecoveryKeyPanel v-model:saved="saved" :recovery-key="key" :email="authStore.user?.email" />
      <UiFormField v-if="needsPassword" label="Password" hint="Confirm it's you to save the key.">
        <UiPasswordInput v-model="password" autocomplete="current-password" />
      </UiFormField>
      <UiAlert v-if="error">{{ error }}</UiAlert>
      <div class="flex justify-end">
        <UiButton type="submit" variant="primary" :disabled="!saved" :loading="busy">Done</UiButton>
      </div>
    </form>
  </UiModal>
</template>
