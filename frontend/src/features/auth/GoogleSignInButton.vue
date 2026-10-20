<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useAuthStore } from "../../stores/auth";
import { renderGoogleButton } from "../../lib/google";

const props = withDefaults(defineProps<{ text?: "signin_with" | "signup_with" | "continue_with"; disabled?: boolean }>(), {
  text: "continue_with",
});
const emit = defineEmits<{ credential: [credential: string] }>();

const authStore = useAuthStore();
const container = ref<HTMLElement | null>(null);
const state = ref<"loading" | "ready" | "unavailable" | "error">("loading");
const errorText = ref("");

async function setup() {
  state.value = "loading";
  await authStore.fetchAuthConfig();
  if (!authStore.googleClientId) {
    state.value = "unavailable";
    return;
  }
  try {
    // The container must be visible to be measured, so mark it ready first.
    state.value = "ready";
    await new Promise((r) => requestAnimationFrame(r));
    await renderGoogleButton({
      clientId: authStore.googleClientId,
      container: container.value!,
      text: props.text,
      onCredential: (credential) => emit("credential", credential),
    });
  } catch (err: any) {
    errorText.value = err.message || "Google sign-in couldn't load.";
    state.value = "error";
  }
}

onMounted(setup);
</script>

<template>
  <div class="w-full">
    <div
      v-show="state === 'ready'"
      ref="container"
      class="flex h-11 w-full justify-center [&>div]:w-full"
      :class="{ 'pointer-events-none opacity-60': disabled }"
    ></div>
    <div v-if="state === 'loading'" class="h-11 w-full animate-pulse rounded-lg bg-slate-100" aria-label="Loading Google sign-in"></div>
    <button
      v-else-if="state === 'unavailable'"
      type="button"
      disabled
      class="btn-secondary btn-lg w-full"
      title="Google sign-in hasn't been set up on this server yet"
    >
      <svg class="h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23z" />
        <path fill="#FBBC05" d="M5.84 14.09A6.6 6.6 0 0 1 5.49 12c0-.73.13-1.43.35-2.09V7.07H2.18A11 11 0 0 0 1 12c0 1.78.43 3.45 1.18 4.93l3.66-2.84z" />
        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1A11 11 0 0 0 2.18 7.07l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38z" />
      </svg>
      Google sign-in unavailable
    </button>
    <div v-else-if="state === 'error'" class="alert-error">
      <span class="flex-1">{{ errorText }}</span>
      <button type="button" class="font-medium underline" @click="setup">Retry</button>
    </div>
  </div>
</template>
