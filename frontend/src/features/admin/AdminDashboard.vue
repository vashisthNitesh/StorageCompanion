<script setup lang="ts">
import { ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { LayoutDashboard, Users, Files } from "lucide-vue-next";
import UiPageHeader from "../../components/ui/UiPageHeader.vue";
import UiTabs from "../../components/ui/UiTabs.vue";
import AdminOverview from "./AdminOverview.vue";
import AdminUsers from "./AdminUsers.vue";
import AdminFiles from "./AdminFiles.vue";

type Tab = "overview" | "users" | "files";
const route = useRoute();
const router = useRouter();
const tabs = [
  { value: "overview", label: "Overview", icon: LayoutDashboard },
  { value: "users", label: "Customers", icon: Users },
  { value: "files", label: "Files", icon: Files },
];
const initial = route.query.tab as Tab;
const tab = ref<string>(tabs.some((t) => t.value === initial) ? initial : "overview");
watch(tab, (next) => router.replace({ query: { ...route.query, tab: next } }));
</script>

<template>
  <div>
    <UiPageHeader title="Admin console" description="Customers, plans, storage pool and platform activity." />
    <div class="mt-6">
      <UiTabs v-model="tab" :tabs="tabs" label="Admin sections" />
    </div>
    <div class="mt-6">
      <KeepAlive>
        <AdminOverview v-if="tab === 'overview'" />
        <AdminUsers v-else-if="tab === 'users'" />
        <AdminFiles v-else />
      </KeepAlive>
    </div>
  </div>
</template>
