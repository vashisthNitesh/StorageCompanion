<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowLeft, ChevronDown, Lock, ImageIcon, Download, Eye, ShieldCheck, Receipt } from "lucide-vue-next";
import UiAlert from "../../components/ui/UiAlert.vue";
import UiButton from "../../components/ui/UiButton.vue";
import PlanCards from "./PlanCards.vue";
import CompareTable from "./CompareTable.vue";
import IntervalToggle from "./IntervalToggle.vue";
import { useAuthStore } from "../../stores/auth";
import { useBillingStore, type Plan } from "../../stores/billing";
import { normalizeApiError } from "../../lib/errors";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const billing = useBillingStore();

const interval = ref<"monthly" | "yearly">(route.query.interval === "monthly" ? "monthly" : "yearly");
const sub = computed(() => authStore.user?.subscription);
const currentCode = computed(() => (sub.value?.has_active_subscription ? sub.value.plan_code : null));
/** Why the person was sent here (e.g. an upload that didn't fit). */
const reason = computed(() => (typeof route.query.reason === "string" ? route.query.reason : ""));

function choose(plan: Plan) {
  void router.push({ name: "checkout", query: { plan: plan.code, interval: interval.value } });
}

const included = [
  { icon: Lock, title: "Encrypted on your device", text: "Files and names are scrambled before they leave your browser." },
  { icon: ImageIcon, title: "Original quality", text: "Nothing is compressed or resized." },
  { icon: Download, title: "Unmetered downloads", text: "No bandwidth limits or fees." },
  { icon: Eye, title: "Previews everywhere", text: "Photos, videos, PDFs and documents in the browser." },
  { icon: ShieldCheck, title: "Two-step verification", text: "Protect sign-in with an authenticator app." },
  { icon: Receipt, title: "GST invoices", text: "Every payment comes with a downloadable invoice." },
];

const faqs = [
  { q: "Do plans renew automatically?", a: "No. Plans are prepaid for a month or a year. We remind you before yours ends, and you can add more time whenever you like." },
  { q: "Can I change plans later?", a: "Yes. Upgrading or switching starts the new plan as soon as you pay. Time left on the old plan isn't carried over, so it's best to switch close to your renewal date." },
  { q: "What does “Add more time” do?", a: "It buys another month or year of the plan you already have. The new time starts when your current period ends, so you don't lose any days." },
  { q: "What happens if my plan ends?", a: "Uploads pause, but your files stay available to download for 90 days. Renew any time in that window to carry on." },
  { q: "Is GST included?", a: "Yes. Prices include 18% GST, and your invoice shows CGST/SGST or IGST for your state." },
];
const openFaq = ref<number | null>(null);

onMounted(() => {
  void billing.ensurePlans();
  void authStore.fetchAuthConfig();
});
</script>

<template>
  <div class="mx-auto max-w-[1400px]">
    <UiButton variant="ghost" size="sm" :icon="ArrowLeft" to="/app/billing" class="-ml-2">Plan & billing</UiButton>

    <header class="mx-auto mt-2 max-w-2xl text-center">
      <h1 class="text-2xl font-semibold tracking-tight text-fg sm:text-3xl">{{ currentCode ? "Change your plan" : "Choose your plan" }}</h1>
      <p class="mt-2 text-base text-fg-muted">Prepaid in rupees, GST included. Plans never renew automatically.</p>
      <div class="mt-5 flex justify-center"><IntervalToggle v-model="interval" /></div>
    </header>

    <UiAlert v-if="reason" tone="info" class="mx-auto mt-6 max-w-2xl">{{ reason }}</UiAlert>
    <UiAlert v-if="billing.plansError" class="mx-auto mt-6 max-w-2xl">
      {{ normalizeApiError(billing.plansError).message }}
      <template #action><UiButton size="sm" @click="billing.fetchPlans()">Retry</UiButton></template>
    </UiAlert>

    <div class="mt-8">
      <PlanCards
        :plans="billing.plans"
        :interval="interval"
        :current-code="currentCode"
        :used-bytes="authStore.user?.quota?.bytes_used"
        :loading="!billing.plansLoaded && !billing.plansError"
        @select="choose"
      />
    </div>

    <!-- Every plan includes -->
    <section class="mt-10 rounded-2xl border border-line bg-surface p-5 sm:p-6" aria-labelledby="included-heading">
      <h2 id="included-heading" class="text-md font-semibold text-fg">Every plan includes</h2>
      <ul class="mt-4 grid gap-x-6 gap-y-5 sm:grid-cols-2 lg:grid-cols-3">
        <li v-for="item in included" :key="item.title" class="flex gap-3">
          <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary-soft text-primary">
            <component :is="item.icon" :size="18" :stroke-width="1.75" aria-hidden="true" />
          </span>
          <div>
            <p class="text-base font-medium text-fg">{{ item.title }}</p>
            <p class="text-sm text-fg-muted">{{ item.text }}</p>
          </div>
        </li>
      </ul>
    </section>

    <!-- Compare -->
    <details v-if="billing.plans.length" class="group mt-6">
      <summary class="inline-flex cursor-pointer select-none items-center gap-1.5 rounded text-base font-medium text-primary hover:underline">
        Compare all plans <ChevronDown :size="16" class="transition-transform group-open:rotate-180" aria-hidden="true" />
      </summary>
      <div class="mt-4"><CompareTable :plans="billing.plans" :current-code="currentCode" /></div>
    </details>

    <!-- Questions -->
    <section class="mx-auto mt-10 max-w-3xl pb-4" aria-labelledby="plan-faq">
      <h2 id="plan-faq" class="text-md font-semibold text-fg">Questions about plans</h2>
      <dl class="mt-4 divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface">
        <div v-for="(f, i) in faqs" :key="f.q">
          <dt>
            <button
              :id="`plan-faq-q-${i}`"
              type="button"
              class="flex w-full items-center justify-between gap-4 px-5 py-4 text-left text-base font-medium text-fg transition-colors hover:bg-canvas-subtle focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary"
              :aria-expanded="openFaq === i"
              :aria-controls="`plan-faq-a-${i}`"
              @click="openFaq = openFaq === i ? null : i"
            >
              {{ f.q }}
              <ChevronDown :size="18" class="shrink-0 text-fg-subtle transition-transform duration-base" :class="{ 'rotate-180': openFaq === i }" aria-hidden="true" />
            </button>
          </dt>
          <dd
            :id="`plan-faq-a-${i}`"
            role="region"
            :aria-labelledby="`plan-faq-q-${i}`"
            class="grid transition-[grid-template-rows] duration-slow ease-out"
            :class="openFaq === i ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'"
          >
            <div class="overflow-hidden">
              <p class="px-5 pb-4 text-base leading-relaxed text-fg-muted" :inert="openFaq !== i || undefined">{{ f.a }}</p>
            </div>
          </dd>
        </div>
      </dl>
    </section>
  </div>
</template>
