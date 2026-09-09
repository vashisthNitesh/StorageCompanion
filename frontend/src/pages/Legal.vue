<script setup lang="ts">
import { ArrowLeft, Lock, ShieldCheck } from "lucide-vue-next";
</script>

<template>
  <div class="min-h-screen bg-[#F8FAFC] text-slate-800 flex flex-col selection:bg-brand-600 selection:text-white">
    <header class="border-b border-slate-200 bg-white/90 sticky top-0 z-30 backdrop-blur-md shadow-xs">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <router-link to="/" class="flex items-center space-x-2 text-slate-600 hover:text-slate-900 text-xs font-semibold transition-colors">
          <ArrowLeft class="w-4 h-4" />
          <span>Back to smartspacedata.com</span>
        </router-link>
        <div class="flex items-center space-x-2">
          <div class="w-7 h-7 rounded-xl bg-brand-600 flex items-center justify-center text-white">
            <Lock class="w-3.5 h-3.5" />
          </div>
          <span class="font-bold text-slate-900 text-sm tracking-tight">SmartSpace Data Legal & Compliance</span>
        </div>
        <div class="w-10"></div>
      </div>
    </header>

    <main class="flex-1 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 w-full space-y-12">
      <div class="space-y-3">
        <div class="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-xs font-mono font-semibold text-emerald-700">
          <ShieldCheck class="w-3.5 h-3.5" />
          <span>DPDP ACT COMPLIANT • SAC CODE 998315</span>
        </div>
        <h1 class="text-3xl font-extrabold text-slate-900 tracking-tight">Privacy Policy & Terms of Service</h1>
        <p class="text-xs text-slate-500">Effective: September 2026 • smartspacedata.com</p>
      </div>

      <section class="space-y-6 text-xs sm:text-sm text-slate-700 leading-relaxed">
        <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-3">
          <h2 class="text-base font-bold text-slate-900">1. DPDP Privacy Act & Zero-Knowledge Architecture</h2>
          <p>
            SmartSpace Data (smartspacedata.com) operates under a mathematical zero-knowledge privacy model fully compliant with India's Digital Personal Data Protection (DPDP) Act. All user files, folder structures, and filenames are encrypted in your local browser using client-derived Argon2id keys and AES-256-GCM before transmission. SmartSpace Data operators possess no master decryption keys and cannot read or profile your data.
          </p>
        </div>

        <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-3">
          <h2 class="text-base font-bold text-slate-900">2. 15-Day Inactivity & Data Clean-Up Protocol</h2>
          <p>
            To deliver an asset-light "Paisa Vasool" service with uncompressed RAW storage at the lowest possible cost (starting at ₹39/month), users agree to our strict data lifecycle policy:
          </p>
          <div class="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900 font-medium">
            "If a subscription is not renewed within 15 days of expiration, user data will be automatically purged from the secure cloud layer to prevent unnecessary infrastructure overhead."
          </div>
          <p>
            Automated alerts will be sent to your registered email address before any purge sequence initiates.
          </p>
        </div>

        <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-3">
          <h2 class="text-base font-bold text-slate-900">3. Zero Egress Bandwidth Policy</h2>
          <p>
            SmartSpace Data does not bill or throttle download bandwidth. Vault owners and authorized share-link recipients are entitled to unmetered, high-speed downloads without hidden fees or per-gigabyte bandwidth surcharges.
          </p>
        </div>

        <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-3">
          <h2 class="text-base font-bold text-slate-900">4. Billing & SAC Code 998315 Classification</h2>
          <p>
            All plans are processed in Indian Rupees (INR) via Razorpay. Services are invoiced under Services Accounting Code (SAC) 998315 (Hosting & IT Infrastructure provisioning services). Business customers with registered GSTINs can claim full Input Tax Credit (ITC) on all recurring subscription charges.
          </p>
        </div>
      </section>
    </main>
  </div>
</template>
