<script setup lang="ts">
import SiteHeader from "./components/SiteHeader.vue";
import SiteFooter from "./components/SiteFooter.vue";
import UiButton from "../components/ui/UiButton.vue";

const principles = [
  { title: "Private by default", text: "Files and file names are encrypted in your browser. We built SmartSpace so that we can't read what you store." },
  { title: "Honest pricing", text: "Prices in rupees, inclusive of all taxes. No bandwidth charges, no surprise renewals." },
  { title: "Built to last", text: "Original quality, version history and 90 days to download your files if a plan ends." },
];
</script>

<template>
  <div class="min-h-screen bg-canvas">
    <SiteHeader />
    <main class="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-16">
      <h1 class="text-4xl font-semibold tracking-tight text-fg">About SmartSpace</h1>
      <p class="mt-4 text-lg leading-relaxed text-fg-muted">
        SmartSpace is private cloud storage made in India. We think your photos, documents and videos should be safe without you having to trust anyone with them,
        including us.
      </p>
      <div class="mt-10 grid gap-4 sm:grid-cols-3">
        <section v-for="p in principles" :key="p.title" class="rounded-2xl border border-line bg-surface p-5">
          <h2 class="text-md font-semibold text-fg">{{ p.title }}</h2>
          <p class="mt-2 text-base leading-relaxed text-fg-muted">{{ p.text }}</p>
        </section>
      </div>
      <div class="mt-10 flex flex-wrap gap-3">
        <UiButton variant="primary" to="/register">Get started</UiButton>
        <UiButton to="/security">How we protect your files</UiButton>
      </div>
    </main>
    <SiteFooter />
  </div>
</template>
