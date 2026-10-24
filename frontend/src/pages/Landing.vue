<script setup lang="ts">
import { ref } from "vue";
import {
  Lock,
  ImageIcon,
  Download,
  FolderTree,
  History,
  Smartphone,
  ArrowRight,
  ChevronDown,
  Upload,
  KeyRound,
  CheckCircle2,
  Check,
  ShieldCheck,
  FileImage,
} from "lucide-vue-next";
import SiteHeader from "./components/SiteHeader.vue";
import SiteFooter from "./components/SiteFooter.vue";
import PlanGrid from "./components/PlanGrid.vue";
import ProductMock from "./components/ProductMock.vue";
import UiButton from "../components/ui/UiButton.vue";
import UiBadge from "../components/ui/UiBadge.vue";
import { vReveal } from "../directives/reveal";
import { useAuthStore } from "../stores/auth";
import { homeFor } from "../router";

const authStore = useAuthStore();

const trust = ["AES-256 in your browser", "UPI, cards and net banking", "GST invoice every time"];

const stats = [
  { value: "AES-256", label: "Encrypted before upload" },
  { value: "₹0", label: "Download or bandwidth fees" },
  { value: "25 GB–1 TB", label: "Plans for every library" },
  { value: "90 days", label: "To download after a plan ends" },
];

const features = [
  { icon: ImageIcon, title: "Original quality, always", text: "No compression. RAW photos, ProRes and 4K video come back bit-for-bit identical." },
  { icon: Download, title: "Unmetered downloads", text: "Download your files as often as you need. No bandwidth charges, ever." },
  { icon: FolderTree, title: "Folders that make sense", text: "Upload whole folders, keep their structure, and find anything with instant search." },
  { icon: History, title: "Version history", text: "Upload a new copy of a file and keep earlier versions you can download anytime." },
  { icon: Smartphone, title: "Preview anywhere", text: "Open photos, videos, PDFs and documents right in your browser, on laptop or phone." },
];

const steps = [
  { icon: KeyRound, title: "Create your account", text: "Sign up with Google or email. Your encryption key is created on your device." },
  { icon: CheckCircle2, title: "Pick a plan", text: "From 25 GB to 1 TB, paid in INR with UPI, cards or net banking." },
  { icon: Upload, title: "Upload and relax", text: "Drag in files or folders. They're encrypted, uploaded and ready anywhere." },
];

const faqs = [
  {
    q: "Can SmartSpace see my files?",
    a: "If you create your account with an email and password, no. Your files and file names are encrypted in your browser with a key that only your password can unlock, so we store data we can't read. Accounts created with Google sign-in use a key we derive for you so you never need a separate password; choose email sign-up if you want the strongest privacy.",
  },
  {
    q: "What happens if I forget my password?",
    a: "Because only your password can unlock your encryption key, we can't reset it for you, and files in a password account can't be recovered without it. Use a password manager, or sign in with Google.",
  },
  { q: "Are downloads really unlimited?", a: "Yes. We don't charge for or throttle downloads. You only pay for the storage your plan includes." },
  {
    q: "What happens when my plan ends?",
    a: "Uploads pause, but your files stay available to download for 90 days. Renew any time in that window to carry on. After 90 days the files are permanently deleted.",
  },
  { q: "Do you compress my photos or videos?", a: "Never. Files are stored exactly as you upload them, so RAW photos, ProRes footage and archives keep their full quality." },
  { q: "Do I get a GST invoice?", a: "Yes. Every payment comes with a downloadable invoice that shows GST for your state." },
];
const openFaq = ref<number | null>(0);
</script>

<template>
  <div class="min-h-screen overflow-x-clip bg-canvas">
    <SiteHeader />

    <!-- Hero -->
    <section class="relative">
      <div class="pointer-events-none absolute inset-0 -z-0 bg-[radial-gradient(60%_50%_at_70%_0%,rgb(var(--primary)/0.14),transparent_70%)]" aria-hidden="true" />
      <div
        class="pointer-events-none absolute inset-0 -z-0 opacity-50 [background-image:radial-gradient(rgb(var(--border-strong)/0.35)_1px,transparent_1px)] [background-size:22px_22px] [mask-image:linear-gradient(to_bottom,black,transparent_70%)]"
        aria-hidden="true"
      />
      <div class="relative mx-auto grid max-w-6xl grid-cols-[minmax(0,1fr)] items-center gap-12 px-4 pb-16 pt-10 sm:px-6 sm:pt-14 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)] lg:gap-10 lg:pb-20">
        <div class="text-center lg:text-left">
          <UiBadge tone="primary" class="animate-slide-up">Made in India · Priced in rupees</UiBadge>
          <h1 class="mt-5 animate-slide-up text-4xl font-semibold tracking-tight text-fg [animation-delay:60ms] sm:text-5xl lg:text-[3.4rem] lg:leading-[1.08]">
            Cloud storage only
            <span class="bg-gradient-to-r from-primary to-violet-500 bg-clip-text text-transparent">you</span>
            can read
          </h1>
          <p class="mx-auto mt-5 max-w-xl animate-slide-up text-lg leading-relaxed text-fg-muted [animation-delay:120ms] lg:mx-0">
            SmartSpace encrypts your photos, videos and documents on your device before they're uploaded. Original quality, unmetered downloads, from ₹39 a month.
          </p>
          <div class="mt-8 flex animate-slide-up flex-col justify-center gap-3 [animation-delay:180ms] sm:flex-row lg:justify-start">
            <UiButton v-if="authStore.isAuthenticated" variant="primary" size="lg" :icon-right="ArrowRight" :to="homeFor(authStore.isMasterAdmin)">
              {{ authStore.isMasterAdmin ? "Open admin console" : "Open my files" }}
            </UiButton>
            <UiButton v-else variant="primary" size="lg" :icon-right="ArrowRight" to="/register">Get started free</UiButton>
            <UiButton size="lg" to="/pricing">See pricing</UiButton>
          </div>
          <ul class="mt-6 flex animate-slide-up flex-wrap justify-center gap-x-5 gap-y-2 text-sm text-fg-muted [animation-delay:240ms] lg:justify-start">
            <li v-for="t in trust" :key="t" class="flex items-center gap-1.5"><Check :size="15" :stroke-width="2.25" class="text-success" aria-hidden="true" />{{ t }}</li>
          </ul>
        </div>

        <div class="animate-slide-up [animation-delay:200ms] lg:pl-4">
          <ProductMock />
        </div>
      </div>
    </section>

    <!-- Stats -->
    <section class="border-y border-line bg-surface" aria-label="At a glance">
      <dl class="mx-auto grid max-w-6xl grid-cols-2 divide-line px-4 sm:px-6 md:grid-cols-4 md:divide-x">
        <div v-for="(s, i) in stats" :key="s.value" v-reveal="i * 60" class="flex flex-col px-2 py-6 text-center md:px-6">
          <dt class="order-2 mt-1 text-sm text-fg-muted">{{ s.label }}</dt>
          <dd class="text-2xl font-semibold tracking-tight text-fg">{{ s.value }}</dd>
        </div>
      </dl>
    </section>

    <!-- Features (bento) -->
    <section id="features" class="scroll-mt-20 py-16 sm:py-20">
      <div class="mx-auto max-w-6xl px-4 sm:px-6">
        <div v-reveal class="mx-auto max-w-2xl text-center">
          <p class="text-sm font-semibold uppercase tracking-wide text-primary">Why SmartSpace</p>
          <h2 class="mt-2 text-3xl font-semibold tracking-tight text-fg sm:text-4xl">Everything your files need, nothing they don't</h2>
          <p class="mt-3 text-lg text-fg-muted">Simple, private storage for creators, photographers and families.</p>
        </div>

        <div class="mt-10 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <!-- Hero feature: encryption, with a small illustration -->
          <article v-reveal class="group relative overflow-hidden rounded-2xl border border-line bg-surface p-6 transition-[border-color,box-shadow,transform] duration-base hover:-translate-y-0.5 hover:border-line-strong hover:shadow-lg md:col-span-2 lg:row-span-2">
            <span class="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-fg"><Lock :size="20" :stroke-width="1.75" aria-hidden="true" /></span>
            <h3 class="mt-4 text-lg font-semibold text-fg">Encrypted before it leaves your device</h3>
            <p class="mt-2 max-w-lg text-base leading-relaxed text-fg-muted">
              Files and file names are encrypted in your browser with AES-256. We only ever store scrambled data, so a breach on our side reveals nothing.
            </p>
            <div class="mt-6 grid items-center gap-3 rounded-xl border border-line bg-canvas p-4 sm:grid-cols-[1fr_auto_1fr]" aria-hidden="true">
              <div class="flex items-center gap-3 rounded-lg border border-line bg-surface p-3">
                <span class="flex h-9 w-9 items-center justify-center rounded-md bg-emerald-500/10 text-emerald-600"><FileImage :size="18" /></span>
                <div class="min-w-0">
                  <p class="truncate text-sm font-medium text-fg">Family_trip_2026.jpg</p>
                  <p class="text-xs text-fg-subtle">On your laptop</p>
                </div>
              </div>
              <span class="mx-auto flex h-9 w-9 items-center justify-center rounded-full bg-primary-soft text-primary transition-transform duration-slow group-hover:rotate-90 max-sm:rotate-90 sm:group-hover:rotate-0">
                <ArrowRight :size="18" />
              </span>
              <div class="flex items-center gap-3 rounded-lg border border-line bg-surface p-3">
                <span class="flex h-9 w-9 items-center justify-center rounded-md bg-fg text-canvas"><ShieldCheck :size="18" /></span>
                <div class="min-w-0">
                  <p class="truncate font-mono text-sm text-fg">9f3a·c71e·04b2·e8d9</p>
                  <p class="text-xs text-fg-subtle">What our servers see</p>
                </div>
              </div>
            </div>
            <router-link to="/security" class="mt-5 inline-flex items-center gap-1.5 text-base font-medium text-primary hover:underline">How encryption works <ArrowRight :size="16" /></router-link>
          </article>

          <article
            v-for="(f, i) in features"
            :key="f.title"
            v-reveal="(i % 3) * 70"
            class="group rounded-2xl border border-line bg-surface p-6 transition-[border-color,box-shadow,transform] duration-base hover:-translate-y-0.5 hover:border-line-strong hover:shadow-lg"
          >
            <span class="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-soft text-primary transition-colors duration-base group-hover:bg-primary group-hover:text-primary-fg">
              <component :is="f.icon" :size="20" :stroke-width="1.75" aria-hidden="true" />
            </span>
            <h3 class="mt-4 text-md font-semibold text-fg">{{ f.title }}</h3>
            <p class="mt-1.5 text-base leading-relaxed text-fg-muted">{{ f.text }}</p>
          </article>
        </div>
      </div>
    </section>

    <!-- How it works -->
    <section class="border-y border-line bg-canvas-subtle py-16 sm:py-20">
      <div class="mx-auto max-w-6xl px-4 sm:px-6">
        <div v-reveal class="mx-auto max-w-2xl text-center">
          <p class="text-sm font-semibold uppercase tracking-wide text-primary">How it works</p>
          <h2 class="mt-2 text-3xl font-semibold tracking-tight text-fg sm:text-4xl">Up and running in minutes</h2>
        </div>
        <ol class="relative mt-10 grid gap-4 md:grid-cols-3">
          <li aria-hidden="true" class="pointer-events-none absolute left-[16%] right-[16%] top-[3.25rem] hidden border-t-2 border-dashed border-line-strong md:block" />
          <li v-for="(s, i) in steps" :key="s.title" v-reveal="i * 90" class="relative rounded-2xl border border-line bg-surface p-6 text-center shadow-xs">
            <span class="relative mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-fg text-canvas shadow-md">
              <component :is="s.icon" :size="22" :stroke-width="1.75" aria-hidden="true" />
              <span class="absolute -right-2 -top-2 flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-fg ring-4 ring-surface">{{ i + 1 }}</span>
            </span>
            <h3 class="mt-4 text-md font-semibold text-fg">{{ s.title }}</h3>
            <p class="mx-auto mt-1.5 max-w-xs text-base text-fg-muted">{{ s.text }}</p>
          </li>
        </ol>
      </div>
    </section>

    <!-- Pricing -->
    <section id="pricing" class="scroll-mt-20 py-16 sm:py-20">
      <div class="mx-auto max-w-6xl px-4 sm:px-6">
        <div v-reveal class="mx-auto max-w-2xl text-center">
          <p class="text-sm font-semibold uppercase tracking-wide text-primary">Pricing</p>
          <h2 class="mt-2 text-3xl font-semibold tracking-tight text-fg sm:text-4xl">Pay for storage, not for downloads</h2>
        </div>
        <div v-reveal class="mt-10"><PlanGrid /></div>
      </div>
    </section>

    <!-- FAQ -->
    <section id="faq" class="scroll-mt-20 border-t border-line bg-canvas-subtle py-16 sm:py-20">
      <div class="mx-auto grid max-w-6xl gap-8 px-4 sm:px-6 lg:grid-cols-[1fr_1.6fr] lg:gap-12">
        <div v-reveal>
          <p class="text-sm font-semibold uppercase tracking-wide text-primary">FAQ</p>
          <h2 class="mt-2 text-3xl font-semibold tracking-tight text-fg">Questions, answered</h2>
          <p class="mt-3 text-base text-fg-muted">Can't find what you're looking for? Read how we protect your files on the <router-link to="/security" class="font-medium text-primary hover:underline">security page</router-link>.</p>
        </div>
        <dl v-reveal class="divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface">
          <div v-for="(f, i) in faqs" :key="f.q">
            <dt>
              <button
                :id="`faq-q-${i}`"
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
                <p class="px-5 pb-5 text-base leading-relaxed text-fg-muted" :inert="openFaq !== i || undefined">{{ f.a }}</p>
              </div>
            </dd>
          </div>
        </dl>
      </div>
    </section>

    <!-- CTA -->
    <section class="px-4 py-16 sm:px-6 sm:py-20">
      <div v-reveal class="relative mx-auto max-w-6xl overflow-hidden rounded-3xl bg-primary px-6 py-12 text-center sm:px-12 sm:py-14">
        <div class="pointer-events-none absolute inset-0 opacity-30 [background-image:radial-gradient(rgb(255_255_255/0.5)_1px,transparent_1px)] [background-size:18px_18px] [mask-image:radial-gradient(60%_80%_at_50%_0%,black,transparent)]" aria-hidden="true" />
        <div class="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-white/10 blur-2xl" aria-hidden="true" />
        <h2 class="relative text-3xl font-semibold tracking-tight text-primary-fg sm:text-4xl">Keep your files private</h2>
        <p class="relative mx-auto mt-3 max-w-xl text-lg text-primary-fg/85">Create your account in under a minute. Choose a plan when you're ready to upload.</p>
        <UiButton class="relative mt-7 border-transparent" size="lg" :icon-right="ArrowRight" to="/register">Get started free</UiButton>
      </div>
    </section>

    <SiteFooter />
  </div>
</template>
