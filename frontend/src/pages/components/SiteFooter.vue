<script setup lang="ts">
import { ShieldCheck } from "lucide-vue-next";
import AppLogo from "../../components/AppLogo.vue";

// Only pages that exist are linked. Contact and the support email appear once
// VITE_SUPPORT_EMAIL is configured.
const supportEmail = (import.meta.env.VITE_SUPPORT_EMAIL as string | undefined)?.trim() || "";

type Link = { label: string; to?: string; href?: string };
const columns: { title: string; links: Link[] }[] = [
  {
    title: "Product",
    links: [
      { label: "Features", to: "/#features" },
      { label: "Pricing", to: "/pricing" },
      { label: "How it works", to: "/#how-it-works" },
      { label: "Security", to: "/security" },
    ],
  },
  {
    title: "Company",
    links: [{ label: "About", to: "/about" }, ...(supportEmail ? [{ label: "Contact", href: `mailto:${supportEmail}` }] : [])],
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy", to: "/legal#privacy" },
      { label: "Terms", to: "/legal#terms" },
    ],
  },
  {
    title: "Support",
    links: [{ label: "FAQ", to: "/#faq" }, ...(supportEmail ? [{ label: supportEmail, href: `mailto:${supportEmail}` }] : [])],
  },
];
</script>

<template>
  <footer class="bg-footer text-footer-fg">
    <div class="mx-auto grid max-w-6xl gap-10 px-4 py-12 sm:px-6 lg:grid-cols-[1.3fr_2fr]">
      <div>
        <AppLogo size="sm" tone="light" />
        <p class="mt-3 max-w-xs text-base leading-relaxed text-footer-muted">Private cloud storage, encrypted before it leaves your device.</p>
        <span class="mt-4 inline-flex items-center gap-1.5 rounded-full border border-footer-line px-3 py-1 text-sm font-medium text-footer-fg">
          <ShieldCheck :size="15" class="text-success" aria-hidden="true" />End-to-end encrypted
        </span>
      </div>
      <nav class="grid grid-cols-2 gap-8 sm:grid-cols-4" aria-label="Footer">
        <div v-for="col in columns" :key="col.title">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-footer-muted">{{ col.title }}</h2>
          <ul class="mt-3 space-y-2.5">
            <li v-for="l in col.links" :key="l.label">
              <router-link v-if="l.to" :to="l.to" class="break-words text-base text-footer-fg/90 transition-colors hover:text-footer-fg hover:underline">{{ l.label }}</router-link>
              <a v-else :href="l.href" class="break-all text-base text-footer-fg/90 transition-colors hover:text-footer-fg hover:underline">{{ l.label }}</a>
            </li>
          </ul>
        </div>
      </nav>
    </div>
    <div class="border-t border-footer-line">
      <div class="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-5 text-sm text-footer-muted sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <p>© {{ new Date().getFullYear() }} SmartSpace · smartspacedata.com</p>
        <p>Made in India</p>
      </div>
    </div>
  </footer>
</template>
