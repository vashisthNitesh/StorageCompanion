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
} from "lucide-vue-next";
import SiteHeader from "./components/SiteHeader.vue";
import SiteFooter from "./components/SiteFooter.vue";
import PlanGrid from "./components/PlanGrid.vue";
import { useAuthStore } from "../stores/auth";
import { homeFor } from "../router";

const authStore = useAuthStore();

const features = [
  { icon: Lock, title: "Encrypted before upload", text: "Files and file names are encrypted in your browser with AES-256. We store only scrambled data." },
  { icon: ImageIcon, title: "Original quality, always", text: "No compression. RAW photos, ProRes and 4K video come back bit-for-bit identical." },
  { icon: Download, title: "Unmetered downloads", text: "Download your files as often as you need. No bandwidth charges, ever." },
  { icon: FolderTree, title: "Folders that make sense", text: "Upload whole folders, keep their structure, and find anything with instant search." },
  { icon: History, title: "Version history", text: "Upload a new copy of a file and keep earlier versions you can download anytime." },
  { icon: Smartphone, title: "Works everywhere", text: "Use it from any modern browser on your laptop or phone. Nothing to install." },
];

const steps = [
  { icon: KeyRound, title: "Create your account", text: "Sign up with Google or email. Your encryption key is created on your device." },
  { icon: CheckCircle2, title: "Pick a plan", text: "From 25 GB to 1 TB, paid in INR with UPI, cards or net banking." },
  { icon: Upload, title: "Upload and relax", text: "Drag in files or folders. They're encrypted, uploaded and ready to download anywhere." },
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
  {
    q: "Are downloads really unlimited?",
    a: "Yes. We don't charge for or throttle downloads. You only pay for the storage your plan includes.",
  },
  {
    q: "What happens when my plan ends?",
    a: "Uploads pause, but your files stay available to download for 90 days. Renew any time in that window to carry on. After 90 days the files are permanently deleted.",
  },
  {
    q: "Do you compress my photos or videos?",
    a: "Never. Files are stored exactly as you upload them, so RAW photos, ProRes footage and archives keep their full quality.",
  },
  {
    q: "Do I get a GST invoice?",
    a: "Yes. Every payment comes with a downloadable invoice that shows GST for your state.",
  },
];
const openFaq = ref<number | null>(0);
</script>

<template>
  <div class="min-h-screen bg-white">
    <SiteHeader />

    <!-- Hero -->
    <section class="relative overflow-hidden">
      <div class="absolute inset-x-0 top-0 -z-0 h-[36rem] bg-gradient-to-b from-brand-50 to-white"></div>
      <div class="relative mx-auto max-w-6xl px-4 pb-20 pt-16 sm:px-6 sm:pt-24 lg:pb-28">
        <div class="mx-auto max-w-3xl text-center">
          <span class="badge-blue">Made in India · Priced in rupees</span>
          <h1 class="mt-6 text-4xl font-semibold tracking-tight text-slate-900 sm:text-6xl">
            Cloud storage that only <span class="text-brand-600">you</span> can read
          </h1>
          <p class="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-slate-600">
            SmartSpace encrypts your photos, videos and documents on your device before they're uploaded. Original quality, unmetered downloads, from ₹39 a month.
          </p>
          <div class="mt-10 flex flex-col justify-center gap-3 sm:flex-row">
            <router-link v-if="authStore.isAuthenticated" :to="homeFor(authStore.isMasterAdmin)" class="btn-primary btn-lg">
              Open my files <ArrowRight class="h-4 w-4" />
            </router-link>
            <router-link v-else to="/register" class="btn-primary btn-lg">Get started <ArrowRight class="h-4 w-4" /></router-link>
            <router-link to="/pricing" class="btn-secondary btn-lg">See pricing</router-link>
          </div>
          <p class="mt-5 text-sm text-slate-500">Sign up free and choose a plan when you're ready to upload.</p>
        </div>

        <!-- Product preview -->
        <div class="mx-auto mt-16 max-w-4xl rounded-2xl border border-slate-200 bg-white p-2 shadow-pop">
          <div class="rounded-xl border border-slate-100 bg-slate-50">
            <div class="flex items-center gap-1.5 border-b border-slate-100 px-4 py-3">
              <span class="h-2.5 w-2.5 rounded-full bg-slate-200"></span><span class="h-2.5 w-2.5 rounded-full bg-slate-200"></span><span class="h-2.5 w-2.5 rounded-full bg-slate-200"></span>
              <span class="ml-3 text-xs text-slate-400">My files / Wedding — Mehta 2026</span>
            </div>
            <ul class="divide-y divide-slate-100 text-left text-sm">
              <li v-for="row in [
                ['Ceremony', 'Folder', '—'],
                ['DSC_0412.ARW', 'Image', '48.2 MB'],
                ['Highlights_4K_final.mov', 'Video', '3.4 GB'],
                ['Contract_signed.pdf', 'PDF', '412 KB'],
              ]" :key="row[0]" class="grid grid-cols-[1fr_auto] items-center gap-4 px-4 py-3 sm:grid-cols-[1fr_120px_100px]">
                <span class="flex items-center gap-3 font-medium text-slate-800">
                  <span class="h-8 w-8 rounded-lg" :class="row[1] === 'Folder' ? 'bg-amber-100' : row[1] === 'Video' ? 'bg-violet-100' : row[1] === 'PDF' ? 'bg-rose-100' : 'bg-emerald-100'"></span>
                  {{ row[0] }}
                </span>
                <span class="hidden text-slate-500 sm:block">{{ row[1] }}</span>
                <span class="text-slate-500">{{ row[2] }}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <!-- Features -->
    <section id="features" class="scroll-mt-20 border-t border-slate-100 bg-slate-50 py-20 sm:py-24">
      <div class="mx-auto max-w-6xl px-4 sm:px-6">
        <div class="mx-auto max-w-2xl text-center">
          <h2 class="text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">Everything your files need, nothing they don't</h2>
          <p class="mt-4 text-lg text-slate-600">Simple, private storage for creators, photographers and families.</p>
        </div>
        <div class="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <div v-for="f in features" :key="f.title" class="card card-body">
            <span class="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50 text-brand-600"><component :is="f.icon" class="h-5 w-5" /></span>
            <h3 class="mt-4 font-semibold text-slate-900">{{ f.title }}</h3>
            <p class="mt-2 text-sm leading-relaxed text-slate-600">{{ f.text }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- How it works -->
    <section class="py-20 sm:py-24">
      <div class="mx-auto max-w-6xl px-4 sm:px-6">
        <h2 class="text-center text-3xl font-semibold tracking-tight text-slate-900">Up and running in minutes</h2>
        <ol class="mt-14 grid gap-10 md:grid-cols-3">
          <li v-for="(s, i) in steps" :key="s.title" class="text-center">
            <span class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-900 text-white"><component :is="s.icon" class="h-5 w-5" /></span>
            <p class="mt-4 text-xs font-medium uppercase tracking-wide text-brand-600">Step {{ i + 1 }}</p>
            <h3 class="mt-1 font-semibold text-slate-900">{{ s.title }}</h3>
            <p class="mx-auto mt-2 max-w-xs text-sm text-slate-600">{{ s.text }}</p>
          </li>
        </ol>
      </div>
    </section>

    <!-- Pricing -->
    <section id="pricing" class="scroll-mt-20 border-t border-slate-100 bg-slate-50 py-20 sm:py-24">
      <div class="mx-auto max-w-6xl px-4 sm:px-6">
        <div class="mx-auto max-w-2xl text-center">
          <h2 class="text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">Simple pricing</h2>
          <p class="mt-4 text-lg text-slate-600">Pay for storage, not for downloads.</p>
        </div>
        <div class="mt-10"><PlanGrid /></div>
      </div>
    </section>

    <!-- FAQ -->
    <section id="faq" class="scroll-mt-20 py-20 sm:py-24">
      <div class="mx-auto max-w-3xl px-4 sm:px-6">
        <h2 class="text-center text-3xl font-semibold tracking-tight text-slate-900">Questions</h2>
        <dl class="mt-10 divide-y divide-slate-200 rounded-2xl border border-slate-200">
          <div v-for="(f, i) in faqs" :key="f.q">
            <dt>
              <button class="flex w-full items-center justify-between gap-4 px-5 py-4 text-left font-medium text-slate-900" :aria-expanded="openFaq === i" @click="openFaq = openFaq === i ? null : i">
                {{ f.q }}
                <ChevronDown class="h-5 w-5 shrink-0 text-slate-400 transition-transform" :class="{ 'rotate-180': openFaq === i }" />
              </button>
            </dt>
            <dd v-if="openFaq === i" class="px-5 pb-5 text-sm leading-relaxed text-slate-600">{{ f.a }}</dd>
          </div>
        </dl>
      </div>
    </section>

    <!-- CTA -->
    <section class="px-4 pb-20 sm:px-6">
      <div class="mx-auto max-w-6xl rounded-3xl bg-slate-900 px-6 py-14 text-center sm:px-12">
        <h2 class="text-3xl font-semibold tracking-tight text-white">Keep your files private</h2>
        <p class="mx-auto mt-3 max-w-xl text-slate-300">Create your account in under a minute.</p>
        <router-link to="/register" class="btn mt-8 h-11 bg-white px-6 text-slate-900 hover:bg-slate-100">Get started <ArrowRight class="h-4 w-4" /></router-link>
      </div>
    </section>

    <SiteFooter />
  </div>
</template>
