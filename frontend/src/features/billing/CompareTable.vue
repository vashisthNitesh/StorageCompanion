<script setup lang="ts">
import { Check } from "lucide-vue-next";
import type { Plan } from "../../stores/billing";
import { formatMoney } from "../../lib/format";
import { INCLUDED_IN_ALL, storageLabel } from "./planCatalog";

defineProps<{ plans: Plan[]; currentCode?: string | null }>();
</script>

<template>
  <div class="relative overflow-x-auto rounded-lg border border-line bg-surface scrollbar-thin">
    <table class="tabular w-full min-w-[640px] text-left text-base">
      <caption class="sr-only">Compare plans</caption>
      <thead>
        <tr class="border-b border-line bg-surface-sunken">
          <th scope="col" class="px-4 py-3 text-sm font-medium text-fg-muted">Feature</th>
          <th v-for="p in plans" :key="p.code" scope="col" class="px-4 py-3 text-sm font-semibold text-fg">
            {{ p.name }}
            <span v-if="p.code === currentCode" class="block text-xs font-normal text-success">Current plan</span>
          </th>
        </tr>
      </thead>
      <tbody class="divide-y divide-line">
        <tr>
          <th scope="row" class="px-4 py-3 font-normal text-fg-muted">Storage</th>
          <td v-for="p in plans" :key="p.code" class="px-4 py-3 font-medium text-fg">{{ storageLabel(p.storage_bytes) }}</td>
        </tr>
        <tr>
          <th scope="row" class="px-4 py-3 font-normal text-fg-muted">Largest file</th>
          <td v-for="p in plans" :key="p.code" class="px-4 py-3 text-fg">{{ storageLabel(p.max_file_size) }}</td>
        </tr>
        <tr>
          <th scope="row" class="px-4 py-3 font-normal text-fg-muted">Version history</th>
          <td v-for="p in plans" :key="p.code" class="px-4 py-3 text-fg">{{ p.version_retention_days }} days</td>
        </tr>
        <tr>
          <th scope="row" class="px-4 py-3 font-normal text-fg-muted">Monthly price</th>
          <td v-for="p in plans" :key="p.code" class="px-4 py-3 text-fg">{{ formatMoney(parseFloat(p.price_monthly)) }}</td>
        </tr>
        <tr>
          <th scope="row" class="px-4 py-3 font-normal text-fg-muted">Yearly price</th>
          <td v-for="p in plans" :key="p.code" class="px-4 py-3 text-fg">{{ formatMoney(parseFloat(p.price_yearly)) }}</td>
        </tr>
        <tr v-for="feature in INCLUDED_IN_ALL" :key="feature">
          <th scope="row" class="px-4 py-3 font-normal text-fg-muted">{{ feature }}</th>
          <td v-for="p in plans" :key="p.code" class="px-4 py-3">
            <Check :size="16" :stroke-width="2.25" class="text-success" aria-label="Included" />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
