<script setup lang="ts">
import { nextTick, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import UiPageHeader from "../../components/ui/UiPageHeader.vue";
import { useAuthStore } from "../../stores/auth";
import PasswordCard from "./PasswordCard.vue";
import TwoStepCard from "./TwoStepCard.vue";
import SessionsCard from "./SessionsCard.vue";
import ActivityCard from "./ActivityCard.vue";

const route = useRoute();
const authStore = useAuthStore();
const sessions = ref<InstanceType<typeof SessionsCard> | null>(null);
const activity = ref<InstanceType<typeof ActivityCard> | null>(null);

function refreshAfterPasswordChange() {
  void sessions.value?.load();
  void activity.value?.load();
}

// Deep links from the command palette (#password, #two-step) scroll inside the app's main area.
onMounted(async () => {
  if (!route.hash) return;
  await nextTick();
  document.querySelector(route.hash)?.scrollIntoView({ behavior: "smooth", block: "start" });
});
</script>

<template>
  <div class="mx-auto max-w-3xl space-y-6">
    <UiPageHeader title="Security" :description="`Signed in as ${authStore.user?.email ?? ''}`" />
    <PasswordCard @changed="refreshAfterPasswordChange" />
    <TwoStepCard />
    <SessionsCard ref="sessions" />
    <ActivityCard ref="activity" />
  </div>
</template>
