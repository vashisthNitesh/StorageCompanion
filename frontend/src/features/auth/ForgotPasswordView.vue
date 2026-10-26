<script setup lang="ts">
import { ref } from "vue";
import { MailCheck } from "lucide-vue-next";
import UiButton from "../../components/ui/UiButton.vue";
import UiFormField from "../../components/ui/UiFormField.vue";
import UiInput from "../../components/ui/UiInput.vue";
import UiAlert from "../../components/ui/UiAlert.vue";
import { rules, useForm } from "../../composables/useForm";
import AuthShell from "./AuthShell.vue";
import { requestPasswordReset } from "./passwordReset";

const sentTo = ref("");
const form = useForm({ email: "" }, { email: [rules.required("Enter your email."), rules.email()] });

async function submit() {
  await form.submit(async (v) => {
    const email = v.email.trim().toLowerCase();
    await requestPasswordReset(email);
    sentTo.value = email;
  });
}
</script>

<template>
  <AuthShell
    :title="sentTo ? 'Check your email' : 'Forgot your password?'"
    :subtitle="sentTo ? undefined : 'We’ll email you a link to choose a new one. Keep your recovery key handy to keep your files.'"
  >
    <div v-if="sentTo" class="space-y-4">
      <p class="flex gap-3 text-base text-fg-muted">
        <MailCheck :size="20" :stroke-width="1.75" class="mt-0.5 shrink-0 text-primary" aria-hidden="true" />
        <span>If an account exists for <strong class="font-medium text-fg">{{ sentTo }}</strong>, we've sent a link to reset the password. It works once and expires in 30 minutes.</span>
      </p>
      <p class="text-sm text-fg-subtle">No email after a few minutes? Check your spam folder, or try again.</p>
      <div class="flex flex-col gap-2 sm:flex-row">
        <UiButton variant="primary" block to="/login">Back to sign in</UiButton>
        <UiButton block @click="sentTo = ''">Try again</UiButton>
      </div>
    </div>
    <form v-else :ref="(el) => (form.formEl.value = el as HTMLFormElement)" novalidate class="space-y-4" @submit.prevent="submit">
      <UiAlert v-if="form.formError.value">{{ form.formError.value }}</UiAlert>
      <UiFormField label="Email" :error="form.errors.email">
        <UiInput v-model="form.values.email" type="email" autocomplete="email" inputmode="email" placeholder="you@example.com" autofocus @blur="form.blur('email')" />
      </UiFormField>
      <UiButton type="submit" variant="primary" size="lg" block :loading="form.submitting.value">Send reset link</UiButton>
    </form>
    <template #footer>
      Remembered it? <router-link to="/login" class="font-medium text-primary hover:underline">Sign in</router-link>
      <span class="mx-1.5 text-fg-subtle">·</span>
      Signed up with Google? <router-link to="/login" class="font-medium text-primary hover:underline">Continue with Google</router-link>
    </template>
  </AuthShell>
</template>
