<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { LayoutDashboard, Users, Files } from "lucide-vue-next";
import AdminOverview from "./AdminOverview.vue";
import AdminUsers from "./AdminUsers.vue";
import AdminFiles from "./AdminFiles.vue";

type Tab = "overview" | "users" | "files";
const route = useRoute();
const router = useRouter();
const tabs = [
  { key: "overview" as const, label: "Overview", icon: LayoutDashboard },
  { key: "users" as const, label: "Customers", icon: Users },
  { key: "files" as const, label: "Files", icon: Files },
];
const initial = route.query.tab as Tab;
const tab = ref<Tab>(tabs.some((t) => t.key === initial) ? initial : "overview");

function select(next: Tab) {
  tab.value = next;
  router.replace({ query: { ...route.query, tab: next } });
}
</script>

<template>
  <div>
    <h1 class="page-title">Admin console</h1>
    <p class="page-subtitle">Customers, plans, storage pool and platform activity.</p>

    <div class="mt-6 border-b border-slate-200">
      <nav class="-mb-px flex gap-6 overflow-x-auto" aria-label="Admin sections">
        <button
          v-for="t in tabs"
          :key="t.key"
          class="inline-flex items-center gap-2 whitespace-nowrap border-b-2 px-1 pb-3 text-sm font-medium"
          :class="tab === t.key ? 'border-brand-600 text-brand-700' : 'border-transparent text-slate-500 hover:text-slate-800'"
          :aria-current="tab === t.key ? 'page' : undefined"
          @click="select(t.key)"
        >
          <component :is="t.icon" class="h-4 w-4" /> {{ t.label }}
        </button>
      </nav>
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
