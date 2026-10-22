<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { MapPinOff } from "lucide-vue-next";
import UiButton from "../components/ui/UiButton.vue";
import StatusScreen from "../components/StatusScreen.vue";
import { useAuthStore } from "../stores/auth";
import { homeFor } from "../router";

const router = useRouter();
const authStore = useAuthStore();
const home = computed(() => (authStore.isAuthenticated ? homeFor(authStore.isMasterAdmin) : "/"));
</script>

<template>
  <StatusScreen :icon="MapPinOff" code="404" title="Page not found" description="The link may be broken, or the page may have moved.">
    <UiButton variant="primary" @click="router.push(home)">{{ !authStore.isAuthenticated ? "Go to home page" : authStore.isMasterAdmin ? "Go to admin console" : "Go to My files" }}</UiButton>
    <UiButton @click="router.back()">Go back</UiButton>
  </StatusScreen>
</template>
