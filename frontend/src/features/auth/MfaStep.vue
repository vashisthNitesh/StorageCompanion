<script setup lang="ts">
import { ref } from "vue";
import { PinInputRoot, PinInputInput } from "reka-ui";
import UiButton from "../../components/ui/UiButton.vue";
import UiFormField from "../../components/ui/UiFormField.vue";
import UiInput from "../../components/ui/UiInput.vue";
import { normalizeApiError } from "../../lib/errors";

// Second sign-in step for accounts with two-step verification. `verify` resolves once signed in.
const props = defineProps<{ verify: (code: string) => Promise<void> }>();
const emit = defineEmits<{ cancel: []; "update:useBackup": [value: boolean] }>();

const pin = ref<(number | undefined)[]>([]);
const backupCode = ref("");
const useBackup = ref(false);
const error = ref("");
const busy = ref(false);

function toggleBackup() {
  useBackup.value = !useBackup.value;
  error.value = "";
  emit("update:useBackup", useBackup.value);
}

async function submit() {
  const code = useBackup.value ? backupCode.value.trim() : pin.value.map((d) => d ?? "").join("");
  if (useBackup.value ? !code : code.length !== 6) {
    error.value = useBackup.value ? "Enter one of your recovery codes." : "Enter all 6 digits.";
    return;
  }
  busy.value = true;
  error.value = "";
  try {
    await props.verify(code);
  } catch (err) {
    const n = normalizeApiError(err);
    error.value = n.kind === "validation" || n.kind === "auth" ? "That code didn't work. Try the newest code from your app." : n.message;
    pin.value = [];
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <form novalidate class="space-y-5" @submit.prevent="submit">
    <UiFormField v-if="useBackup" label="Recovery code" :error="error">
      <UiInput v-model="backupCode" autocomplete="one-time-code" autofocus spellcheck="false" />
    </UiFormField>
    <div v-else>
      <PinInputRoot v-model="pin" otp type="number" placeholder="·" class="flex justify-between gap-2" aria-label="6-digit code" @complete="submit">
        <PinInputInput
          v-for="(_, i) in 6"
          :key="i"
          :index="i"
          :autofocus="i === 0"
          :aria-label="`Digit ${i + 1}`"
          :aria-invalid="!!error || undefined"
          class="h-12 w-full rounded border bg-surface text-center font-mono text-lg text-fg shadow-xs outline-none focus:border-primary focus:ring-4 focus:ring-primary/15"
          :class="error ? 'border-danger' : 'border-line-strong'"
        />
      </PinInputRoot>
      <p v-if="error" class="mt-2 text-sm text-danger" role="alert">{{ error }}</p>
    </div>
    <UiButton type="submit" variant="primary" size="lg" block :loading="busy">Verify and sign in</UiButton>
    <div class="flex justify-between">
      <UiButton variant="link" size="sm" @click="toggleBackup">{{ useBackup ? "Use authenticator code" : "Use a recovery code" }}</UiButton>
      <UiButton variant="link" size="sm" @click="emit('cancel')">Back</UiButton>
    </div>
  </form>
</template>
