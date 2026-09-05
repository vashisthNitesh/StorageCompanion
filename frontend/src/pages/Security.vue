<script setup lang="ts">
import { ShieldCheck, Lock, Key, ArrowLeft, AlertTriangle } from "lucide-vue-next";
</script>

<template>
  <div class="min-h-screen bg-[#070D1A] text-slate-100 flex flex-col">
    <!-- Top Nav -->
    <header class="border-b border-slate-800/80 bg-[#070D1A]/80 sticky top-0 z-30">
      <div class="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        <router-link to="/" class="flex items-center space-x-2 text-slate-300 hover:text-white text-sm font-medium">
          <ArrowLeft class="w-4 h-4" />
          <span>Back to Home</span>
        </router-link>
        <span class="font-bold text-white tracking-tight">SpeedCloud Security Architecture</span>
        <router-link to="/register" class="text-sm font-semibold text-brand-400 hover:text-brand-300">
          Get Started
        </router-link>
      </div>
    </header>

    <main class="flex-1 max-w-4xl mx-auto px-4 py-16 w-full space-y-12">
      <div class="text-center space-y-4">
        <div class="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-brand-500/10 border border-brand-500/30 text-xs font-semibold text-brand-400">
          <ShieldCheck class="w-4 h-4" />
          <span>Zero-Knowledge Cryptographic Spec</span>
        </div>
        <h1 class="text-4xl font-extrabold text-white tracking-tight">
          How Your Data Stays Completely Private
        </h1>
        <p class="text-slate-300 text-base max-w-2xl mx-auto">
          We built SpeedCloud so that no rogue operator, compromised database, or government warrant can expose your files.
        </p>
      </div>

      <!-- Warning Box: Zero-Knowledge Trade-offs -->
      <div class="p-6 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-sm space-y-2">
        <div class="flex items-center space-x-2 font-bold text-amber-400">
          <AlertTriangle class="w-5 h-5" />
          <span>Important Zero-Knowledge Caveats</span>
        </div>
        <p class="text-xs text-amber-200/90 leading-relaxed">
          Because we cannot read your Master Key or your password, <strong>password reset is cryptographically impossible without your 24-word recovery phrase</strong>. When signing up, you will be required to write down and securely backup this phrase. If you lose both your password and your recovery phrase, your data is permanently lost.
        </p>
      </div>

      <!-- Deep Dive Grid -->
      <div class="space-y-8">
        <div class="p-8 rounded-3xl glass-card border border-slate-800 space-y-4">
          <div class="flex items-center space-x-3 text-brand-400">
            <Lock class="w-6 h-6" />
            <h2 class="text-xl font-bold text-white">1. Key Derivation (Argon2id in WebAssembly)</h2>
          </div>
          <p class="text-sm text-slate-300 leading-relaxed">
            When you enter your password in your browser, the client runs Argon2id using WebAssembly (64 MB RAM cost, 3 iterations). This derives a 256-bit Key Encryption Key (KEK) that exists only in your browser's memory. Your plain password is never sent as your encryption key.
          </p>
        </div>

        <div class="p-8 rounded-3xl glass-card border border-slate-800 space-y-4">
          <div class="flex items-center space-x-3 text-brand-400">
            <Key class="w-6 h-6" />
            <h2 class="text-xl font-bold text-white">2. Per-File Random AES-256-GCM Keys</h2>
          </div>
          <p class="text-sm text-slate-300 leading-relaxed">
            Every file you upload is assigned a brand new 256-bit random File Key generated via <code>crypto.getRandomValues()</code>. Files are split into 8 MB or 16 MB chunks in a background Web Worker, encrypted with AES-256-GCM using deterministic nonces, and sent directly to R2.
          </p>
        </div>

        <div class="p-8 rounded-3xl glass-card border border-slate-800 space-y-4">
          <div class="flex items-center space-x-3 text-brand-400">
            <ShieldCheck class="w-6 h-6" />
            <h2 class="text-xl font-bold text-white">3. Encrypted Names & Client-Side Search</h2>
          </div>
          <p class="text-sm text-slate-300 leading-relaxed">
            File and folder names are encrypted with your Master Key before saving to the database. The server sees only Base64 ciphertext. To provide lightning-fast search, your browser decrypts names and maintains a local index inside your browser's IndexedDB.
          </p>
        </div>
      </div>
    </main>
  </div>
</template>
