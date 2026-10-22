<script setup lang="ts">
import { KeyRound, Smartphone, LifeBuoy } from "lucide-vue-next";
import UiButton from "../../components/ui/UiButton.vue";
import AuthShell from "./AuthShell.vue";
</script>

<template>
  <AuthShell title="Forgot your password?" subtitle="Your password is the key that encrypts your files, so SmartSpace never sees it and can't reset it.">
    <ul class="space-y-4 text-base">
      <li class="flex gap-3">
        <KeyRound :size="18" :stroke-width="1.75" class="mt-0.5 shrink-0 text-primary" aria-hidden="true" />
        <span class="text-fg-muted"><strong class="font-medium text-fg">Try your password manager.</strong> Search for “SmartSpace” in your browser or password manager.</span>
      </li>
      <li class="flex gap-3">
        <Smartphone :size="18" :stroke-width="1.75" class="mt-0.5 shrink-0 text-primary" aria-hidden="true" />
        <span class="text-fg-muted"><strong class="font-medium text-fg">Still signed in somewhere?</strong> You can set a new password from Security on any device where you're signed in.</span>
      </li>
      <li class="flex gap-3">
        <LifeBuoy :size="18" :stroke-width="1.75" class="mt-0.5 shrink-0 text-primary" aria-hidden="true" />
        <span class="text-fg-muted"><strong class="font-medium text-fg">Need help?</strong> Support can close your account so you can start again, but files encrypted with the old password can't be recovered.</span>
      </li>
    </ul>
    <UiButton class="mt-6" variant="primary" size="lg" block @click="$router.push('/login')">Back to sign in</UiButton>
    <template #footer>
      Signed in with Google? <router-link to="/login" class="font-medium text-primary hover:underline">Continue with Google</router-link>
    </template>
  </AuthShell>
</template>
