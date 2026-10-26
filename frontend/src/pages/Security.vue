<script setup lang="ts">
import { KeyRound, LifeBuoy, Link2, Lock, Server, ShieldCheck, Smartphone } from "lucide-vue-next";
import SiteHeader from "./components/SiteHeader.vue";
import SiteFooter from "./components/SiteFooter.vue";

const points = [
  {
    icon: KeyRound,
    title: "Your key is made on your device",
    text: "When you sign up with email, your browser creates a random 256-bit key for your vault and locks it with a key derived from your password using Argon2id. We only ever store the locked version. Your password never leaves your device: to sign in, your browser sends a separate key derived from it.",
  },
  {
    icon: LifeBuoy,
    title: "A recovery key only you hold",
    text: "At sign-up you get a recovery key that also unlocks your vault. If you forget your password, an emailed link plus your recovery key lets you choose a new one in your browser. We never see the key, so without it we can restore your account but not your files.",
  },
  {
    icon: Lock,
    title: "Files are encrypted before upload",
    text: "Each file gets its own key and is encrypted with AES-256-GCM in 20 MB pieces before it leaves your device. File and folder names are encrypted too.",
  },
  {
    icon: Link2,
    title: "Links we can't open",
    text: "When you share a file, your browser makes a new key for the link and puts it after the # in the address, which browsers never send to servers. Add a password, an expiry or a download limit, and turn the link off at any time.",
  },
  {
    icon: Server,
    title: "We store data we can't read",
    text: "Our servers and our storage provider hold only encrypted bytes. Decryption happens in your browser when you download.",
  },
  {
    icon: ShieldCheck,
    title: "Protected sign-in",
    text: "Optional two-step verification with an authenticator app, automatic lock-out after repeated wrong passwords, and the ability to sign out any device instantly.",
  },
  {
    icon: Smartphone,
    title: "Short-lived sessions",
    text: "Sign-in tokens last 30 minutes and are renewed through a secure, HTTP-only cookie. Signing out or revoking a device ends its session immediately.",
  },
];
</script>

<template>
  <div class="min-h-screen bg-canvas">
    <SiteHeader />
    <main class="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-16">
      <h1 class="text-4xl font-semibold tracking-tight text-fg">How we protect your files</h1>
      <p class="mt-4 text-lg text-fg-muted">SmartSpace is built so your files stay private, even from us.</p>

      <ul class="mt-10 space-y-6">
        <li v-for="p in points" :key="p.title" class="flex gap-4">
          <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary-soft text-primary"><component :is="p.icon" :size="20" :stroke-width="1.75" aria-hidden="true" /></span>
          <div>
            <h2 class="text-md font-semibold text-fg">{{ p.title }}</h2>
            <p class="mt-1 leading-relaxed text-fg-muted">{{ p.text }}</p>
          </div>
        </li>
      </ul>

    </main>
    <SiteFooter />
  </div>
</template>
