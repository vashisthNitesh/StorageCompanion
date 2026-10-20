<script setup lang="ts">
import { ref, onMounted } from "vue";
import { Check } from "lucide-vue-next";
import { useBillingStore, type Plan } from "../../stores/billing";
import { useAuthStore } from "../../stores/auth";
import { formatMoney } from "../../lib/format";

const billing = useBillingStore();
const authStore = useAuthStore();
const interval = ref<"monthly" | "yearly">("yearly");
const loading = ref(!billing.plans.length);
const featured = "value";

function storageLabel(bytes: number) {
  const gb = bytes / 1024 ** 3;
  return gb >= 1000 ? `${(gb / 1000).toFixed(gb % 1000 ? 1 : 0)} TB` : `${Math.round(gb)} GB`;
}
function price(p: Plan) {
  return parseFloat(interval.value === "yearly" ? p.price_yearly : p.price_monthly);
}
function link(p: Plan) {
  return authStore.isAuthenticated ? { path: "/app/billing", query: { plan: p.code } } : { path: "/register", query: { plan: p.code } };
}

onMounted(async () => {
  if (!billing.plans.length) await billing.fetchPlans();
  loading.value = false;
});
</script>

<template>
  <div>
    <div class="flex justify-center">
      <div class="inline-flex rounded-full border border-slate-200 bg-white p-1" role="group" aria-label="Billing period">
        <button
          v-for="opt in (['monthly', 'yearly'] as const)"
          :key="opt"
          class="h-9 rounded-full px-4 text-sm font-medium"
          :class="interval === opt ? 'bg-slate-900 text-white' : 'text-slate-600 hover:text-slate-900'"
          :aria-pressed="interval === opt"
          @click="interval = opt"
        >
          {{ opt === "monthly" ? "Monthly" : "Yearly · 2 months free" }}
        </button>
      </div>
    </div>

    <div v-if="billing.plansError" class="alert-error mx-auto mt-8 max-w-md">
      {{ billing.plansError }} <button class="ml-1 underline" @click="billing.fetchPlans()">Retry</button>
    </div>

    <div class="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      <template v-if="loading">
        <div v-for="i in 5" :key="i" class="h-80 animate-pulse rounded-2xl bg-white ring-1 ring-slate-200"></div>
      </template>
      <article
        v-for="p in billing.plans"
        v-else
        :key="p.code"
        class="relative flex flex-col rounded-2xl bg-white p-6"
        :class="p.code === featured ? 'ring-2 ring-brand-600 shadow-pop lg:-my-3 lg:py-9' : 'ring-1 ring-slate-200'"
      >
        <span v-if="p.code === featured" class="absolute -top-3 left-6 rounded-full bg-brand-600 px-3 py-1 text-xs font-medium text-white">Most popular</span>
        <h3 class="text-sm font-medium text-slate-600">{{ p.name }}</h3>
        <p class="mt-1 text-3xl font-semibold tracking-tight text-slate-900">{{ storageLabel(p.storage_bytes) }}</p>
        <p class="mt-4">
          <span class="text-2xl font-semibold text-slate-900">{{ formatMoney(price(p), p.currency) }}</span>
          <span class="text-sm text-slate-500"> / {{ interval === "yearly" ? "year" : "month" }}</span>
        </p>
        <p class="mt-3 text-sm text-slate-500">{{ p.description }}</p>
        <ul class="mt-5 flex-1 space-y-2.5 text-sm text-slate-700">
          <li class="flex gap-2"><Check class="mt-0.5 h-4 w-4 shrink-0 text-brand-600" />Files up to {{ storageLabel(p.max_file_size) }}</li>
          <li class="flex gap-2"><Check class="mt-0.5 h-4 w-4 shrink-0 text-brand-600" />{{ p.version_retention_days }}-day version history</li>
          <li class="flex gap-2"><Check class="mt-0.5 h-4 w-4 shrink-0 text-brand-600" />End-to-end encrypted</li>
          <li class="flex gap-2"><Check class="mt-0.5 h-4 w-4 shrink-0 text-brand-600" />Unmetered downloads</li>
        </ul>
        <router-link :to="link(p)" class="mt-6 w-full" :class="p.code === featured ? 'btn-primary' : 'btn-secondary'">
          Choose {{ p.name.replace(" Pack", "") }}
        </router-link>
      </article>
    </div>
    <p class="mt-6 text-center text-sm text-slate-500">Prices in INR, GST included. Pay with UPI, cards or net banking.</p>
  </div>
</template>
