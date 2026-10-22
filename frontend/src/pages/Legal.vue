<script setup lang="ts">
import SiteHeader from "./components/SiteHeader.vue";
import SiteFooter from "./components/SiteFooter.vue";

const sections = [
  {
    title: "1. The service",
    body: [
      "SmartSpace (smartspacedata.com) provides encrypted cloud storage. You get the amount of storage included in your plan for the period you pay for.",
    ],
  },
  {
    title: "2. Your privacy",
    body: [
      "Files and file names are encrypted in your browser before upload. For accounts created with email and password, we cannot decrypt them. For accounts created with Google sign-in, the vault key is derived on our servers so that you don't need a separate password.",
      "We store your email address, name, encrypted keys, file sizes and dates, payment records, and a log of account activity (such as sign-ins and uploads with IP address) to run and secure the service. We don't sell your data or use it for advertising.",
      "We process personal data in line with India's Digital Personal Data Protection Act, 2023. To ask about, correct or delete your data, contact us from your registered email address.",
    ],
  },
  {
    title: "3. When a plan ends",
    body: [
      "When your plan ends, uploads pause and your files stay available to download for 90 days. If you don't renew within those 90 days, your files are permanently deleted and cannot be recovered.",
    ],
  },
  {
    title: "4. Payments and invoices",
    body: [
      "Plans are priced in Indian Rupees and include GST. Payments are processed by Razorpay. Plans don't renew automatically. Each payment comes with a downloadable invoice showing the tax for your state.",
    ],
  },
  {
    title: "5. Acceptable use",
    body: [
      "Don't use SmartSpace to store or distribute content that is illegal or infringes others' rights. We may suspend accounts that break these terms or the law.",
    ],
  },
  {
    title: "6. Your responsibility",
    body: [
      "Keep your password safe. Because we can't reset it, losing the password of an email account means losing access to its files. We recommend keeping your own backup of anything irreplaceable.",
    ],
  },
];
</script>

<template>
  <div class="min-h-screen bg-canvas">
    <SiteHeader />
    <main class="mx-auto max-w-3xl px-4 py-16 sm:px-6 sm:py-20">
      <h1 class="text-4xl font-semibold tracking-tight text-fg">Terms & privacy</h1>
      <p class="mt-3 text-sm text-fg-subtle">Last updated October 2026</p>
      <div class="mt-10 space-y-10">
        <section v-for="s in sections" :key="s.title">
          <h2 class="text-lg font-semibold text-fg">{{ s.title }}</h2>
          <p v-for="(p, i) in s.body" :key="i" class="mt-3 leading-relaxed text-fg-muted">{{ p }}</p>
        </section>
      </div>
    </main>
    <SiteFooter />
  </div>
</template>
