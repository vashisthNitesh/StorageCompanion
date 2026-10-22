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
  <div class="min-h-screen bg-canvas">
    <SiteHeader />
    <main class="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
      <div class="mx-auto max-w-2xl text-center">
        <h1 class="text-4xl font-semibold tracking-tight text-fg sm:text-5xl">Pricing</h1>
        <p class="mt-4 text-lg text-fg-muted">One price for storage. Downloads are always free.</p>
      </div>
      <div class="mt-12"><PlanGrid compare /></div>

      <section class="mx-auto mt-20 max-w-4xl">
        <h2 class="text-center text-2xl font-semibold tracking-tight text-fg">How SmartSpace compares</h2>
        <div class="mt-8 rounded-lg border border-line bg-surface shadow-xs overflow-x-auto">
          <table class="w-full min-w-[560px] text-left text-base">
            <thead class="border-b border-line text-fg-subtle">
              <tr>
                <th scope="col" class="px-5 py-3 font-medium"><span class="sr-only">Feature</span></th>
                <th scope="col" class="px-5 py-3 font-semibold text-primary">SmartSpace</th>
                <th scope="col" class="px-5 py-3 font-medium">Consumer photo clouds</th>
                <th scope="col" class="px-5 py-3 font-medium">Business object storage</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-line">
              <tr v-for="r in rows" :key="r[0]">
                <th scope="row" class="px-5 py-3 font-medium text-fg">{{ r[0] }}</th>
                <td v-for="(cell, i) in r.slice(1)" :key="i" class="px-5 py-3" :class="i === 0 ? 'bg-primary-soft/50' : ''">
                  <Check v-if="cell === true" :size="20" class="text-success" aria-label="Yes" />
                  <Minus v-else-if="cell === false" :size="20" class="text-fg-subtle" aria-label="No" />
                  <span v-else class="text-fg-muted">{{ cell }}</span>
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
