<script setup lang="ts">
import { ShieldCheck, Gauge, Download } from "lucide-vue-next";
import AppLogo from "../../components/AppLogo.vue";

defineProps<{ title: string; subtitle?: string }>();

const points = [
  { icon: ShieldCheck, title: "Encrypted on your device", text: "Files and names are encrypted in your browser before they're uploaded." },
  { icon: Gauge, title: "Original quality", text: "Nothing is compressed. RAW photos and 4K video stay bit-for-bit identical." },
  { icon: Download, title: "Unmetered downloads", text: "Download your files as often as you like at no extra cost." },
];
</script>

<template>
  <div class="min-h-screen bg-white lg:grid lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
    <aside class="relative hidden overflow-hidden bg-slate-900 lg:flex lg:flex-col lg:justify-between p-12 text-white">
      <div class="absolute -right-40 -top-40 h-[28rem] w-[28rem] rounded-full bg-brand-600/30 blur-3xl"></div>
      <div class="absolute -bottom-48 -left-24 h-[24rem] w-[24rem] rounded-full bg-sky-500/20 blur-3xl"></div>
      <router-link to="/" class="relative"><AppLogo tone="light" /></router-link>
      <div class="relative max-w-md">
        <h2 class="text-3xl font-semibold leading-tight tracking-tight">Private cloud storage that only you can read.</h2>
        <ul class="mt-10 space-y-6">
          <li v-for="p in points" :key="p.title" class="flex gap-4">
            <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white/10">
              <component :is="p.icon" class="h-5 w-5" />
            </span>
            <span>
              <span class="block font-medium">{{ p.title }}</span>
              <span class="mt-0.5 block text-sm text-slate-300">{{ p.text }}</span>
            </span>
          </li>
        </ul>
      </div>
      <p class="relative text-xs text-slate-400">© {{ new Date().getFullYear() }} SmartSpace · smartspacedata.com</p>
    </aside>

    <main class="flex min-h-screen flex-col px-4 py-8 sm:px-8">
      <router-link to="/" class="lg:hidden"><AppLogo /></router-link>
      <div class="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-10">
        <h1 class="text-2xl font-semibold tracking-tight text-slate-900">{{ title }}</h1>
        <p v-if="subtitle" class="mt-2 text-sm text-slate-500">{{ subtitle }}</p>
        <div class="mt-8">
          <slot />
        </div>
      </div>
    </main>
  </div>
</template>
