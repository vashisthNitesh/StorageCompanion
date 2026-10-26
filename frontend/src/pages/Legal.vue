<script setup lang="ts">
import SiteHeader from "./components/SiteHeader.vue";
import SiteFooter from "./components/SiteFooter.vue";

const groups = [
  {
    id: "privacy",
    title: "Privacy",
    sections: [
      {
        title: "Encryption",
        body: [
          "Files and file names are encrypted in your browser before upload. For accounts created with email and password, we cannot decrypt them: your password and recovery key never reach us in a form we can use. For accounts created with Google sign-in, the vault key is derived on our servers so that you don't need a separate password.",
          "Shared links carry their decryption key after the # in the address, which browsers never send to our servers.",
        ],
      },
      {
        title: "What we store",
        body: [
          "We store your email address, name, encrypted keys, file sizes and dates, payment records, and a log of account activity (such as sign-ins and uploads with IP address) to run and secure the service. We don't sell your data or use it for advertising.",
        ],
      },
      {
        title: "Your rights",
        body: [
          "We process personal data in line with India's Digital Personal Data Protection Act, 2023. To ask about, correct or delete your data, contact us from your registered email address.",
        ],
      },
    ],
  },
  {
    id: "terms",
    title: "Terms of service",
    sections: [
      {
        title: "1. The service",
        body: [
          "SmartSpace (smartspacedata.com) provides encrypted cloud storage. You get the amount of storage included in your plan for the period you pay for.",
        ],
      },
      {
        title: "2. When a plan ends",
        body: [
          "When your plan ends, uploads pause and your files stay available to download for 90 days. If you don't renew within those 90 days, your files are permanently deleted and cannot be recovered.",
        ],
      },
      {
        title: "3. Payments and invoices",
        body: [
          "Plans are priced in Indian Rupees. All prices are final and inclusive of all taxes; nothing is added at checkout. Yearly plans cost ten times the monthly price for twelve months. Payments are processed by Razorpay. Plans don't renew automatically. Each payment comes with a downloadable invoice.",
        ],
      },
      {
        title: "4. Sharing",
        body: [
          "You are responsible for the links you share and who you share them with. You can revoke a link at any time; anyone who already downloaded the file keeps their copy.",
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
          "Keep your password and recovery key safe. We can't recover either of them. If you lose both, you can reset access to your account, but files uploaded before can't be decrypted. We recommend keeping your own backup of anything irreplaceable.",
        ],
      },
    ],
  },
];
</script>

<template>
  <div class="min-h-screen bg-canvas">
    <SiteHeader />
    <main class="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-16">
      <h1 class="text-4xl font-semibold tracking-tight text-fg">Privacy & terms</h1>
      <p class="mt-3 text-sm text-fg-subtle">Last updated October 2026</p>
      <nav class="mt-6 flex gap-4 text-base font-medium" aria-label="On this page">
        <a v-for="g in groups" :key="g.id" :href="`#${g.id}`" class="text-primary hover:underline">{{ g.title }}</a>
      </nav>
      <section v-for="g in groups" :id="g.id" :key="g.id" class="mt-10 scroll-mt-20" :aria-labelledby="`${g.id}-h`">
        <h2 :id="`${g.id}-h`" class="text-2xl font-semibold tracking-tight text-fg">{{ g.title }}</h2>
        <div class="mt-6 space-y-8">
          <section v-for="s in g.sections" :key="s.title">
            <h3 class="text-lg font-semibold text-fg">{{ s.title }}</h3>
            <p v-for="(p, i) in s.body" :key="i" class="mt-3 leading-relaxed text-fg-muted">{{ p }}</p>
          </section>
        </div>
      </section>
    </main>
    <SiteFooter />
  </div>
</template>
