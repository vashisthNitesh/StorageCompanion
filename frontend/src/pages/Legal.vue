<script setup lang="ts">
import { ArrowLeft } from "lucide-vue-next";
</script>

<template>
  <div class="min-h-screen bg-[#070D1A] text-slate-100 flex flex-col">
    <header class="border-b border-slate-800/80 bg-[#070D1A]/80 sticky top-0 z-30">
      <div class="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        <router-link to="/" class="flex items-center space-x-2 text-slate-300 hover:text-white text-sm font-medium">
          <ArrowLeft class="w-4 h-4" />
          <span>Back to Home</span>
        </router-link>
        <span class="font-bold text-white tracking-tight">SpeedCloud Legal & Privacy</span>
        <div class="w-10"></div>
      </div>
    </header>

    <main class="flex-1 max-w-4xl mx-auto px-4 py-16 w-full space-y-12">
      <div class="space-y-4">
        <h1 class="text-3xl font-extrabold text-white">Privacy Policy & Terms of Service</h1>
        <p class="text-sm text-slate-400">Effective: September 2026</p>
      </div>

      <section class="space-y-4 text-sm text-slate-300 leading-relaxed">
        <h2 class="text-xl font-bold text-white">1. Zero Operator Surveillance Principle</h2>
        <p>
          SpeedCloud is built on mathematical zero-knowledge guarantees. We do not inspect, log, profile, sell, or analyze your files. File contents and file names are encrypted on your local device before transmission. We possess no decryption keys.
        </p>

        <h2 class="text-xl font-bold text-white mt-8">2. Data We Collect</h2>
        <p>
          We collect only the minimum metadata required to operate your subscription:
        </p>
        <ul class="list-disc pl-5 space-y-1">
          <li>Account email address for authentication and billing notices.</li>
          <li>Encrypted ciphertext blobs and cryptographic salts.</li>
          <li>Aggregate byte storage counts for quota enforcement.</li>
          <li>Payment transaction IDs provided by Razorpay.</li>
        </ul>

        <h2 class="text-xl font-bold text-white mt-8">3. Data Processing Agreement (DPA)</h2>
        <p>
          All stored bytes reside in ISO 27001 and SOC 2 Type II certified datacenters. Because data is encrypted with client-derived keys prior to arrival, processing is limited to storing binary chunks.
        </p>
      </section>
    </main>
  </div>
</template>
