<script setup lang="ts">
import { Check, Minus } from "lucide-vue-next";
import SiteHeader from "./components/SiteHeader.vue";
import SiteFooter from "./components/SiteFooter.vue";
import PlanGrid from "./components/PlanGrid.vue";

const rows: [string, boolean | string, boolean | string, boolean | string][] = [
  ["Download charges", "None", "Often limited", "Per-GB fees"],
  ["Original quality kept", true, "Varies", true],
  ["Encrypted before upload", true, false, false],
  ["Priced in INR with GST invoice", true, "Varies", false],
  ["Pay with UPI", true, "Varies", false],
];
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <SiteHeader />
    <main class="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
      <div class="mx-auto max-w-2xl text-center">
        <h1 class="text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl">Pricing</h1>
        <p class="mt-4 text-lg text-slate-600">One price for storage. Downloads are always free.</p>
      </div>
      <div class="mt-12"><PlanGrid /></div>

      <section class="mx-auto mt-20 max-w-4xl">
        <h2 class="text-center text-2xl font-semibold tracking-tight text-slate-900">How SmartSpace compares</h2>
        <div class="mt-8 card overflow-x-auto">
          <table class="w-full min-w-[560px] text-left text-sm">
            <thead class="border-b border-slate-200 text-slate-500">
              <tr>
                <th class="px-5 py-3 font-medium"></th>
                <th class="px-5 py-3 font-semibold text-brand-700">SmartSpace</th>
                <th class="px-5 py-3 font-medium">Consumer photo clouds</th>
                <th class="px-5 py-3 font-medium">Business object storage</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr v-for="r in rows" :key="r[0]">
                <td class="px-5 py-3 font-medium text-slate-800">{{ r[0] }}</td>
                <td v-for="(cell, i) in r.slice(1)" :key="i" class="px-5 py-3" :class="i === 0 ? 'bg-brand-50/50' : ''">
                  <Check v-if="cell === true" class="h-5 w-5 text-emerald-600" aria-label="Yes" />
                  <Minus v-else-if="cell === false" class="h-5 w-5 text-slate-300" aria-label="No" />
                  <span v-else class="text-slate-600">{{ cell }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>
    <SiteFooter />
  </div>
</template>
