<script setup lang="ts">
import { ShieldCheck, Lock, Key, ArrowLeft, AlertTriangle } from "lucide-vue-next";
</script>

<template>
  <div class="min-h-screen bg-[#F8FAFC] text-slate-800 flex flex-col selection:bg-brand-600 selection:text-white">
    <!-- Top Nav -->
    <header class="border-b border-slate-200 bg-white/90 sticky top-0 z-30 backdrop-blur-md shadow-xs">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <router-link to="/" class="flex items-center space-x-2 text-slate-600 hover:text-slate-900 text-xs font-semibold transition-colors">
          <ArrowLeft class="w-4 h-4" />
          <span>Back to smartspacedata.com</span>
        </router-link>
        <span class="font-bold text-slate-900 text-sm tracking-tight">SmartSpace Data Security Architecture</span>
        <router-link to="/register" class="text-xs font-semibold text-brand-600 hover:text-brand-700 transition-colors">
          Get Started
        </router-link>
      </div>
    </header>

    <main class="flex-1 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 w-full space-y-12">
      <div class="text-center space-y-3">
        <div class="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-xs font-mono font-semibold text-emerald-700">
          <ShieldCheck class="w-3.5 h-3.5" />
          <span>DPDP ACT COMPLIANT • ZERO-KNOWLEDGE SPEC</span>
        </div>
        <h1 class="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
          How Your Data Stays 100% Private
        </h1>
        <p class="text-slate-600 text-xs sm:text-sm max-w-2xl mx-auto leading-relaxed">
          Engineered so no operator, third-party hosting layer, or external entity can inspect your uncompressed RAW files.
        </p>
      </div>

      <!-- Warning Box: Zero-Knowledge Trade-offs -->
      <div class="p-5 rounded-2xl bg-amber-50 border border-amber-200 text-amber-900 text-xs space-y-2 shadow-xs">
        <div class="flex items-center space-x-2 font-bold text-amber-800">
          <AlertTriangle class="w-4 h-4 text-amber-600" />
          <span>Critical Zero-Knowledge Operational Rule</span>
        </div>
        <p class="leading-relaxed">
          Because SmartSpace Data cannot read your Master Key or your password, <strong>password recovery is cryptographically impossible without your 24-word recovery phrase</strong>. When registering, you must record and securely back up this phrase. If you lose both your password and your recovery phrase, your vault cannot be recovered.
        </p>
      </div>

      <!-- Deep Dive Grid -->
      <div class="space-y-6">
        <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs hover:shadow-sm transition-all space-y-3">
          <div class="flex items-center space-x-2.5 text-brand-600">
            <Lock class="w-5 h-5" />
            <h2 class="text-base font-bold text-slate-900">1. Client Key Derivation (Argon2id in WebAssembly)</h2>
          </div>
          <p class="text-xs text-slate-600 leading-relaxed">
            When you enter your password in your browser, the client runs Argon2id using WebAssembly (64 MB RAM cost, 3 iterations). This derives a 256-bit Key Encryption Key (KEK) that exists strictly in your local device memory. Your plaintext password is never used as a database encryption key.
          </p>
        </div>

        <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs hover:shadow-sm transition-all space-y-3">
          <div class="flex items-center space-x-2.5 text-brand-600">
            <Key class="w-5 h-5" />
            <h2 class="text-base font-bold text-slate-900">2. 100% RAW Uncompressed AES-256-GCM Slicing</h2>
          </div>
          <p class="text-xs text-slate-600 leading-relaxed">
            Every file you upload is assigned a brand new 256-bit random File Key generated via <code>crypto.getRandomValues()</code>. Files are split into chunks in a background Web Worker, encrypted with AES-256-GCM using deterministic nonces, and sent directly to presigned storage with zero compression.
          </p>
        </div>

        <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs hover:shadow-sm transition-all space-y-3">
          <div class="flex items-center space-x-2.5 text-brand-600">
            <ShieldCheck class="w-5 h-5" />
            <h2 class="text-base font-bold text-slate-900">3. Encrypted Metadata & Client-Side Search</h2>
          </div>
          <p class="text-xs text-slate-600 leading-relaxed">
            File and folder names are encrypted with your Master Key before saving to the database. The server sees only Base64 ciphertext. To provide instant search without privacy leakage, your browser decrypts names and maintains a local index inside IndexedDB.
          </p>
        </div>
      </div>
    </main>
  </div>
</template>
