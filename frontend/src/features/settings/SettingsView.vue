<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import UiPageHeader from "../../components/ui/UiPageHeader.vue";
import { useAuthStore } from "../../stores/auth";
import PasswordCard from "./PasswordCard.vue";
import TwoStepCard from "./TwoStepCard.vue";
import SessionsCard from "./SessionsCard.vue";
import ActivityCard from "./ActivityCard.vue";
import SecurityOverview from "./SecurityOverview.vue";

const route = useRoute();
const authStore = useAuthStore();
const sessions = ref<InstanceType<typeof SessionsCard> | null>(null);
const activity = ref<InstanceType<typeof ActivityCard> | null>(null);
const twoStep = ref<InstanceType<typeof TwoStepCard> | null>(null);
const deviceCount = computed(() => (sessions.value && !sessions.value.loading ? sessions.value.sessions.length : null));

function jump(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

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
  <div class="max-w-[1400px] space-y-5">
    <UiPageHeader title="Security" :description="`Signed in as ${authStore.user?.email ?? ''}`" />
    <SecurityOverview :device-count="deviceCount" @setup-two-step="twoStep?.startSetup()" @jump="jump" />
    <div class="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
      <div class="space-y-5">
        <PasswordCard @changed="refreshAfterPasswordChange" />
        <TwoStepCard ref="twoStep" />
      </div>
      <div class="space-y-5">
        <SessionsCard ref="sessions" />
        <ActivityCard ref="activity" />
      </div>
    </div>
  </div>
</template>
