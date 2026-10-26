<script setup lang="ts">
import { ref } from "vue";
import { Lock, Share2, ImageIcon, Download, Eye, History, ArrowRight, ChevronDown, UserPlus, Upload, Globe, Check } from "lucide-vue-next";
import SiteHeader from "./components/SiteHeader.vue";
import SiteFooter from "./components/SiteFooter.vue";
import PlanGrid from "./components/PlanGrid.vue";
import UiButton from "../components/ui/UiButton.vue";
import { vReveal } from "../directives/reveal";
import { useAuthStore } from "../stores/auth";
import { homeFor } from "../router";

const authStore = useAuthStore();

const trust = ["End-to-end encrypted", "No hidden charges", "Never auto-renews"];

const steps = [
  { icon: UserPlus, title: "Create your account", text: "Sign up in under a minute with email or Google." },
  { icon: Upload, title: "Upload your files", text: "Encrypted in your browser before they're uploaded." },
  { icon: Globe, title: "Access & share anywhere", text: "Open on any device, share with a secure link." },
];

const features = [
  { icon: Lock, title: "Encrypted before upload", text: "Files and names are encrypted on your device. We store only data we can't read." },
  { icon: Share2, title: "Secure sharing", text: "Share a link that expires, needs a password or limits downloads. The key never reaches us." },
  { icon: ImageIcon, title: "Original quality", text: "No compression. Photos and 4K video come back exactly as you uploaded them." },
  { icon: Download, title: "Unmetered downloads", text: "Download as often as you need. No bandwidth charges." },
  { icon: Eye, title: "Preview anywhere", text: "Open photos, videos, PDFs and documents right in the browser." },
  { icon: History, title: "Version history", text: "Upload a new copy and keep earlier versions you can download." },
];

// Ordered by what people ask first; yes/no answers lead with the answer.
const faqs: { q: string; lead?: string; a: string }[] = [
  {
    q: "Can SmartSpace see my files?",
    lead: "No.",
    a: "If you sign up with email and password, your files and file names are encrypted in your browser with a key that only your password can unlock. We never see your files.",
  },
  { q: "How does yearly billing work?", lead: "You pay for 10 months and get 12.", a: "The yearly price is the monthly price × 10, charged once for the whole year." },
  { q: "Are there any taxes or extra charges?", lead: "No.", a: "The price you see is the price you pay. Nothing is added at checkout." },
  {
    q: "I forgot my password. Can I reset it?",
    lead: "Yes, with your recovery key.",
    a: "We give you a recovery key when you sign up. With it you can choose a new password and keep all your files. Without it you can still get back into your account, but files uploaded before can't be decrypted, because only your password or recovery key can unlock them.",
  },
  {
    q: "Can I share files with people who don't have an account?",
    lead: "Yes.",
    a: "Create a secure link for any file. Add an expiry, a password or a download limit, and revoke it whenever you like. The decryption key is part of the link, so we can't open the file.",
  },
  { q: "Is there a limit on file size?", a: "Each plan has a per-file limit, from 5 GB on Entry to 100 GB on Mega. Storage and file limits are listed on every plan." },
  {
    q: "Do plans renew automatically?",
    lead: "No.",
    a: "Plans are prepaid for a month or a year, so there's nothing to cancel. Add more time whenever you want to keep going.",
  },
  { q: "What happens when my plan ends?", a: "Uploads pause, but your files stay available to download for 90 days. Renew in that time to carry on." },
  { q: "Do you compress my photos or videos?", lead: "No.", a: "Files are stored exactly as you upload them, so RAW photos and 4K footage keep their full quality." },
];
const openFaq = ref<number | null>(0);
</script>

<template>
  <div class="min-h-screen overflow-x-clip bg-canvas">
    <SiteHeader />

    <!-- Hero -->
    <section class="relative">
      <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(55%_60%_at_50%_0%,rgb(var(--highlight)/0.12),transparent_70%)]" aria-hidden="true" />
      <div class="relative mx-auto max-w-3xl px-4 pb-14 pt-14 text-center sm:px-6 sm:pb-16 sm:pt-20">
        <h1 class="animate-slide-up text-balance text-4xl font-semibold tracking-tight text-fg sm:text-5xl lg:text-6xl">
          Your files. <span class="text-highlight">Your key.</span><br class="hidden sm:block" />
          <span class="whitespace-nowrap">No one else's.</span>
        </h1>
        <p class="mx-auto mt-5 max-w-2xl animate-slide-up text-lg leading-relaxed text-fg-muted [animation-delay:80ms]">
          SmartSpace encrypts your files in your browser, so not even we can read them. Simple plans, no hidden charges.
        </p>
        <div class="mt-8 flex animate-slide-up flex-col justify-center gap-3 [animation-delay:140ms] sm:flex-row">
          <UiButton v-if="authStore.isAuthenticated" variant="primary" size="lg" :icon-right="ArrowRight" :to="homeFor(authStore.isMasterAdmin)">
            {{ authStore.isMasterAdmin ? "Open admin console" : "Open my files" }}
          </UiButton>
          <UiButton v-else variant="primary" size="lg" :icon-right="ArrowRight" to="/register">Get started</UiButton>
          <UiButton size="lg" href="#pricing">See pricing</UiButton>
        </div>
        <ul class="mt-6 flex animate-slide-up flex-wrap justify-center gap-x-5 gap-y-2 text-sm text-fg-muted [animation-delay:200ms]">
          <li v-for="t in trust" :key="t" class="flex items-center gap-1.5"><Check :size="15" :stroke-width="2.5" class="text-success" aria-hidden="true" />{{ t }}</li>
        </ul>
      </div>
    </section>

    <!-- Pricing -->
    <section id="pricing" class="scroll-mt-20 border-t border-line bg-canvas-subtle py-14 sm:py-16" aria-labelledby="pricing-heading">
      <div class="mx-auto max-w-6xl px-4 sm:px-6">
        <div class="mx-auto max-w-2xl text-center">
          <h2 id="pricing-heading" class="text-3xl font-semibold tracking-tight text-fg sm:text-4xl">
            “Paisa vasool” <span class="text-highlight">pricing</span>
          </h2>
          <p class="mt-3 text-lg text-fg-muted">Pay for storage, not downloads. Pick monthly, or pay for 10 months and get 12.</p>
        </div>
        <div class="mt-8"><PlanGrid /></div>
      </div>
    </section>

    <!-- 3 easy steps -->
    <section id="how-it-works" class="scroll-mt-20 py-14 sm:py-16" aria-labelledby="steps-heading">
      <div class="mx-auto max-w-5xl px-4 sm:px-6">
        <div class="mx-auto max-w-2xl text-center">
          <h2 id="steps-heading" class="text-3xl font-semibold tracking-tight text-fg sm:text-4xl">Start in <span class="text-highlight">3 easy steps</span></h2>
          <p class="mt-3 text-lg text-fg-muted">Store and share your files securely in minutes.</p>
        </div>
        <ol class="relative mt-10 grid gap-5 md:grid-cols-3 md:gap-6">
          <!-- connecting line: vertical on mobile, horizontal on desktop -->
          <li aria-hidden="true" class="pointer-events-none absolute bottom-10 left-[2.15rem] top-10 w-0.5 bg-gradient-to-b from-highlight/50 to-highlight/10 md:hidden" />
          <li aria-hidden="true" class="pointer-events-none absolute left-[16%] right-[16%] top-[2.6rem] hidden h-0.5 bg-gradient-to-r from-highlight/20 via-highlight/60 to-highlight/20 md:block" />
          <li
            v-for="(s, i) in steps"
            :key="s.title"
            v-reveal="i * 100"
            class="relative flex gap-4 rounded-2xl border border-line bg-surface p-5 shadow-xs md:flex-col md:items-center md:text-center"
          >
            <span class="relative z-10 flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-highlight text-base font-semibold text-white shadow-md ring-4 ring-surface">
              {{ i + 1 }}
            </span>
            <div>
              <h3 class="flex items-center gap-2 text-md font-semibold text-fg md:justify-center">
                <component :is="s.icon" :size="18" :stroke-width="1.85" class="text-primary" aria-hidden="true" />{{ s.title }}
              </h3>
              <p class="mt-1 text-base text-fg-muted">{{ s.text }}</p>
            </div>
          </li>
        </ol>
      </div>
    </section>

    <!-- Features -->
    <section id="features" class="scroll-mt-20 border-t border-line bg-canvas-subtle py-14 sm:py-16" aria-labelledby="features-heading">
      <div class="mx-auto max-w-6xl px-4 sm:px-6">
        <div class="mx-auto max-w-3xl text-center">
          <h2 id="features-heading" class="text-balance text-3xl font-semibold tracking-tight text-fg sm:text-4xl">Private by design, simple to use</h2>
          <p class="mt-3 text-lg text-fg-muted">Everything your files need, nothing they don't.</p>
        </div>
        <div class="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <article
            v-for="(f, i) in features"
            :key="f.title"
            v-reveal="(i % 3) * 70"
            class="group rounded-2xl border border-line bg-surface p-5 transition-[border-color,box-shadow] duration-base hover:border-line-strong hover:shadow-md"
          >
            <span class="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-soft text-primary transition-colors duration-base group-hover:bg-primary group-hover:text-primary-fg">
              <component :is="f.icon" :size="20" :stroke-width="1.75" aria-hidden="true" />
            </span>
            <h3 class="mt-4 text-md font-semibold text-fg">{{ f.title }}</h3>
            <p class="mt-1 text-base leading-relaxed text-fg-muted">{{ f.text }}</p>
          </article>
        </div>
      </div>
    </section>

    <!-- FAQ -->
    <section id="faq" class="scroll-mt-20 py-14 sm:py-16" aria-labelledby="faq-heading">
      <div class="mx-auto max-w-3xl px-4 sm:px-6">
        <h2 id="faq-heading" class="text-center text-3xl font-semibold tracking-tight text-fg sm:text-4xl">Questions, answered</h2>
        <dl class="mt-8 divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface">
          <div v-for="(f, i) in faqs" :key="f.q">
            <dt>
              <button
                :id="`faq-q-${i}`"
                type="button"
                class="flex w-full items-center justify-between gap-4 px-5 py-4 text-left text-md font-medium text-fg transition-colors hover:bg-canvas-subtle focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary"
                :aria-expanded="openFaq === i"
                :aria-controls="`faq-a-${i}`"
                @click="openFaq = openFaq === i ? null : i"
              >
                {{ f.q }}
                <ChevronDown :size="20" aria-hidden="true" class="shrink-0 text-fg-subtle transition-transform duration-base" :class="{ 'rotate-180': openFaq === i }" />
              </button>
            </dt>
            <dd
              :id="`faq-a-${i}`"
              role="region"
              :aria-labelledby="`faq-q-${i}`"
              class="grid transition-[grid-template-rows] duration-slow ease-out"
              :class="openFaq === i ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'"
            >
              <div class="overflow-hidden">
                <p class="px-5 pb-5 text-base leading-relaxed text-fg-muted" :inert="openFaq !== i || undefined">
                  <strong v-if="f.lead" class="font-semibold text-fg">{{ f.lead }}</strong> {{ f.a }}
                </p>
              </div>
            </dd>
          </div>
        </dl>
      </div>
    </section>

    <!-- Final CTA -->
    <section class="px-4 pb-14 sm:px-6 sm:pb-16">
      <div v-reveal class="mx-auto flex max-w-6xl flex-col items-center justify-between gap-5 rounded-2xl bg-primary px-6 py-8 text-center sm:flex-row sm:px-10 sm:text-left">
        <p class="text-xl font-semibold tracking-tight text-primary-fg sm:text-2xl">Your files, encrypted before they leave your device.</p>
        <UiButton class="shrink-0 border-transparent" size="lg" :icon-right="ArrowRight" :to="authStore.isAuthenticated ? homeFor(authStore.isMasterAdmin) : '/register'">
          {{ authStore.isAuthenticated ? "Open my files" : "Get started" }}
        </UiButton>
      </div>
    </section>

    <SiteFooter />
  </div>
</template>
