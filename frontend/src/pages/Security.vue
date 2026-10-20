<script setup lang="ts">
import { KeyRound, Lock, Server, ShieldCheck, Smartphone, AlertTriangle } from "lucide-vue-next";
import SiteHeader from "./components/SiteHeader.vue";
import SiteFooter from "./components/SiteFooter.vue";

const points = [
  {
    icon: KeyRound,
    title: "Your key is made on your device",
    text: "When you sign up with email, your browser creates a random 256-bit key for your vault and locks it with a key derived from your password using Argon2id. We only ever store the locked version.",
  },
  {
    icon: Lock,
    title: "Files are encrypted before upload",
    text: "Each file gets its own key and is encrypted with AES-256-GCM in 20 MB pieces before it leaves your device. File and folder names are encrypted too.",
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
  <div class="min-h-screen bg-white">
    <SiteHeader />
    <main class="mx-auto max-w-3xl px-4 py-16 sm:px-6 sm:py-20">
      <h1 class="text-4xl font-semibold tracking-tight text-slate-900">How we protect your files</h1>
      <p class="mt-4 text-lg text-slate-600">SmartSpace is built so your files stay private, even from us.</p>

      <ul class="mt-12 space-y-8">
        <li v-for="p in points" :key="p.title" class="flex gap-4">
          <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600"><component :is="p.icon" class="h-5 w-5" /></span>
          <div>
            <h2 class="font-semibold text-slate-900">{{ p.title }}</h2>
            <p class="mt-1 leading-relaxed text-slate-600">{{ p.text }}</p>
          </div>
        </li>
      </ul>

      <div class="mt-12 rounded-2xl border border-amber-200 bg-amber-50 p-6">
        <h2 class="flex items-center gap-2 font-semibold text-amber-900"><AlertTriangle class="h-5 w-5" /> Two things to know</h2>
        <ul class="mt-3 list-disc space-y-2 pl-5 text-sm leading-relaxed text-amber-900">
          <li><strong>We can't reset your password.</strong> In an email account, your password is the only way to unlock your files. If you forget it, they can't be recovered.</li>
          <li>
            <strong>Google sign-in trades some privacy for convenience.</strong> Accounts created with Google don't have a separate password, so their vault key is derived on our
            servers. Files are still encrypted at rest, but for the strongest privacy create your account with email and a password.
          </li>
        </ul>
      </div>
    </main>
    <SiteFooter />
  </div>
</template>
