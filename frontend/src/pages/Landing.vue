<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import {
  ShieldCheck,
  Lock,
  Zap,
  Key,
  HardDrive,
  Search,
  CheckCircle2,
  ArrowRight,
  HelpCircle,
  CreditCard,
  Layers,
  ChevronDown,
  Terminal,
} from "lucide-vue-next";

const router = useRouter();
const billingInterval = ref<"monthly" | "yearly">("monthly");
const openFaqIndex = ref<number | null>(null);

function toggleFaq(index: number) {
  openFaqIndex.value = openFaqIndex.value === index ? null : index;
}

function selectPlan(planCode: string) {
  router.push({
    path: "/register",
    query: { plan: planCode, interval: billingInterval.value },
  });
}

const faqs = [
  {
    q: "Can SpeedCloud administrators read my files or recover my password?",
    a: "No. SpeedCloud operates under a strict zero-knowledge model. Your vault encryption key is derived entirely in your browser using Argon2id and never leaves your device. If you forget your password, you must use your offline 24-word recovery phrase.",
  },
  {
    q: "How does payment work with Razorpay?",
    a: "We support seamless INR payments via Razorpay including UPI (Google Pay, PhonePe, Paytm, BHIM, CRED), Indian & international debit/credit cards (RuPay, Visa, Mastercard), and Netbanking across all major banks. Activation is instantaneous upon payment confirmation.",
  },
  {
    q: "Why is there no free tier on SpeedCloud?",
    a: "Free cloud storage providers subsidize costs by mining user telemetry, selling marketing data, or injecting ads. SpeedCloud is a pure privacy-first service sustained exclusively by transparent subscription fees. We treat your data as strictly private property.",
  },
  {
    q: "What are the file size and bandwidth limits?",
    a: "Personal plans support single files up to 10 GB with 200 GB total quota. Business plans support files up to 50 GB with 2 TB quota. There are absolutely zero bandwidth throttles and zero egress fees.",
  },
];
</script>

<template>
  <div class="min-h-screen flex flex-col bg-surface-ground text-slate-100 selection:bg-brand-600 selection:text-white">
    <!-- Navbar -->
    <header class="sticky top-0 z-40 bg-surface-ground/90 backdrop-blur-md border-b border-surface-border">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <!-- Logo -->
        <router-link to="/" class="flex items-center space-x-2.5 group">
          <div class="w-8 h-8 rounded-lg bg-brand-600 border border-white/20 flex items-center justify-center shadow-sm">
            <Lock class="w-4 h-4 text-white" />
          </div>
          <span class="text-lg font-bold tracking-tight text-white">
            Speed<span class="text-brand-400">Cloud</span>
          </span>
          <span class="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-surface-elevated border border-surface-border text-slate-400">
            Zero-Knowledge
          </span>
        </router-link>

        <!-- Nav links -->
        <nav class="hidden md:flex items-center space-x-7 text-xs font-medium text-slate-300">
          <a href="#features" class="hover:text-white transition-colors">Architecture</a>
          <a href="#pricing" class="hover:text-white transition-colors">Pricing</a>
          <router-link to="/security" class="hover:text-white transition-colors">Security Whitepaper</router-link>
          <a href="#faq" class="hover:text-white transition-colors">FAQ</a>
        </nav>

        <!-- Actions -->
        <div class="flex items-center space-x-3">
          <router-link
            to="/login"
            class="px-3.5 py-1.5 text-xs font-medium text-slate-300 hover:text-white transition-colors"
          >
            Log in
          </router-link>
          <button
            @click="selectPlan('personal')"
            class="btn-primary px-4 py-2 rounded-lg text-xs font-semibold text-white flex items-center space-x-1.5"
          >
            <span>Get Started</span>
            <ArrowRight class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </header>

    <!-- Hero Section -->
    <section class="pt-16 pb-20 border-b border-surface-border relative overflow-hidden">
      <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-6">
        <!-- Badge -->
        <div class="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-surface-card border border-surface-border text-[11px] font-medium text-slate-300">
          <span class="w-2 h-2 rounded-full bg-accent-emerald animate-pulse"></span>
          <span>Argon2id + AES-256-GCM Client Encryption</span>
          <span class="text-slate-600">•</span>
          <span class="text-brand-400 font-semibold">Strictly Private</span>
        </div>

        <!-- Headline -->
        <h1 class="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-tight">
          The private cloud storage <br class="hidden sm:block" />
          <span class="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-sky-300 to-indigo-300">
            engineered for zero trust.
          </span>
        </h1>

        <!-- Subtitle -->
        <p class="text-base sm:text-lg text-slate-400 max-w-2xl mx-auto font-normal leading-relaxed">
          Files are encrypted directly in your browser before upload. Our servers only ever store ciphertext blocks. No telemetry, no scanning, and zero egress fees.
        </p>

        <!-- CTAs -->
        <div class="flex flex-col sm:flex-row items-center justify-center space-y-3 sm:space-y-0 sm:space-x-4 pt-2">
          <button
            @click="selectPlan('personal')"
            class="w-full sm:w-auto btn-primary px-6 py-3.5 rounded-xl text-sm font-semibold text-white flex items-center justify-center space-x-2"
          >
            <span>Activate Personal Vault (₹199/mo)</span>
            <ArrowRight class="w-4 h-4" />
          </button>
          <router-link
            to="/security"
            class="w-full sm:w-auto btn-secondary px-6 py-3.5 rounded-xl text-sm font-semibold text-slate-200 flex items-center justify-center space-x-2"
          >
            <ShieldCheck class="w-4 h-4 text-slate-400" />
            <span>Read Cryptographic Spec</span>
          </router-link>
        </div>

        <!-- Trust Badges -->
        <div class="pt-6 flex flex-wrap items-center justify-center gap-6 text-xs text-slate-400">
          <div class="flex items-center space-x-2">
            <CheckCircle2 class="w-4 h-4 text-accent-emerald" />
            <span>24-Word Offline Recovery Phrase</span>
          </div>
          <div class="flex items-center space-x-2">
            <CheckCircle2 class="w-4 h-4 text-accent-emerald" />
            <span>Direct S3/R2 Multipart Uploads</span>
          </div>
          <div class="flex items-center space-x-2">
            <CheckCircle2 class="w-4 h-4 text-accent-emerald" />
            <span>Native Razorpay UPI & Cards</span>
          </div>
        </div>

        <!-- Interactive Architecture Pipeline Diagram -->
        <div class="pt-8 max-w-4xl mx-auto text-left">
          <div class="vault-panel rounded-2xl p-5 border border-surface-border">
            <div class="flex items-center justify-between pb-3 border-b border-surface-border text-xs text-slate-400">
              <div class="flex items-center space-x-2">
                <Terminal class="w-4 h-4 text-brand-400" />
                <span class="font-mono font-medium text-slate-200">Zero-Knowledge Data Flow</span>
              </div>
              <span class="font-mono text-[11px] text-accent-emerald">Encrypted Client-Side</span>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 text-xs">
              <!-- Step 1 -->
              <div class="p-3.5 rounded-xl bg-surface-card border border-surface-border space-y-1.5">
                <div class="font-mono text-[10px] text-brand-400 font-bold">01. IN YOUR BROWSER</div>
                <div class="font-semibold text-white">Argon2id & Key Derivation</div>
                <p class="text-slate-400 text-[11px]">
                  Master key is derived from your password with 64 MB memory cost. Never sent over the wire.
                </p>
              </div>

              <!-- Step 2 -->
              <div class="p-3.5 rounded-xl bg-surface-card border border-surface-border space-y-1.5">
                <div class="font-mono text-[10px] text-brand-400 font-bold">02. CHUNKED ENCRYPTION</div>
                <div class="font-semibold text-white">AES-256-GCM Slicing</div>
                <p class="text-slate-400 text-[11px]">
                  Files split into 5MB chunks. Each chunk receives a distinct deterministic nonce and authentication tag.
                </p>
              </div>

              <!-- Step 3 -->
              <div class="p-3.5 rounded-xl bg-surface-card border border-surface-border space-y-1.5">
                <div class="font-mono text-[10px] text-brand-400 font-bold">03. DIRECT TO STORAGE</div>
                <div class="font-semibold text-white">Presigned Object Store</div>
                <p class="text-slate-400 text-[11px]">
                  Ciphertext streams directly to storage via presigned URLs. Zero server interception possible.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Architecture & Features Grid -->
    <section id="features" class="py-20 border-b border-surface-border">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center max-w-2xl mx-auto space-y-3 mb-14">
          <h2 class="text-2xl sm:text-3xl font-extrabold text-white">
            Built for security purists.
          </h2>
          <p class="text-sm text-slate-400">
            Every architectural decision prioritizes privacy, auditability, and verifiable zero-trust cryptography.
          </p>
        </div>

        <div class="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div class="vault-card p-6 rounded-2xl space-y-3">
            <div class="w-9 h-9 rounded-lg bg-surface-subtle border border-surface-border flex items-center justify-center text-brand-400">
              <Key class="w-5 h-5" />
            </div>
            <h3 class="text-sm font-bold text-white">24-Word Recovery Gate</h3>
            <p class="text-xs text-slate-400 leading-relaxed">
              Mandatory BIP-39 recovery mnemonic generated offline during signup. No backdoors for anyone, including us.
            </p>
          </div>

          <div class="vault-card p-6 rounded-2xl space-y-3">
            <div class="w-9 h-9 rounded-lg bg-surface-subtle border border-surface-border flex items-center justify-center text-brand-400">
              <Search class="w-5 h-5" />
            </div>
            <h3 class="text-sm font-bold text-white">Decrypted Client Search</h3>
            <p class="text-xs text-slate-400 leading-relaxed">
              File names are decrypted into a local browser IndexedDB cache. Your search queries never hit our servers.
            </p>
          </div>

          <div class="vault-card p-6 rounded-2xl space-y-3">
            <div class="w-9 h-9 rounded-lg bg-surface-subtle border border-surface-border flex items-center justify-center text-brand-400">
              <Layers class="w-5 h-5" />
            </div>
            <h3 class="text-sm font-bold text-white">X25519 Link Sharing</h3>
            <p class="text-xs text-slate-400 leading-relaxed">
              Share encrypted files via URL fragments (`#key=...`). The decryption secret stays strictly in the browser hash.
            </p>
          </div>

          <div class="vault-card p-6 rounded-2xl space-y-3">
            <div class="w-9 h-9 rounded-lg bg-surface-subtle border border-surface-border flex items-center justify-center text-brand-400">
              <CreditCard class="w-4 h-4" />
            </div>
            <h3 class="text-sm font-bold text-white">Native Razorpay Billing</h3>
            <p class="text-xs text-slate-400 leading-relaxed">
              Seamless INR payments via UPI (Google Pay, PhonePe, Paytm), RuPay, Visa, Mastercard, and Netbanking.
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- Pricing Section -->
    <section id="pricing" class="py-20 border-b border-surface-border bg-surface-card/40">
      <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center max-w-2xl mx-auto space-y-4 mb-12">
          <h2 class="text-2xl sm:text-3xl font-extrabold text-white">
            Transparent subscription pricing.
          </h2>
          <p class="text-sm text-slate-400">
            No ads, no data monetization, no free tier compromises. Cancel anytime with a single click.
          </p>

          <!-- Interval switch -->
          <div class="inline-flex items-center p-1 rounded-xl bg-surface-card border border-surface-border text-xs">
            <button
              @click="billingInterval = 'monthly'"
              class="px-4 py-1.5 rounded-lg font-semibold transition-all"
              :class="billingInterval === 'monthly' ? 'bg-surface-elevated text-white shadow-sm' : 'text-slate-400 hover:text-white'"
            >
              Monthly Billing
            </button>
            <button
              @click="billingInterval = 'yearly'"
              class="px-4 py-1.5 rounded-lg font-semibold transition-all flex items-center space-x-1.5"
              :class="billingInterval === 'yearly' ? 'bg-surface-elevated text-white shadow-sm' : 'text-slate-400 hover:text-white'"
            >
              <span>Yearly (Save 16%)</span>
              <span class="px-1.5 py-0.2 rounded bg-brand-600/20 text-brand-400 text-[10px] font-bold">BEST VALUE</span>
            </button>
          </div>
        </div>

        <!-- Pricing Cards -->
        <div class="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          <!-- Personal Plan -->
          <div class="vault-panel rounded-2xl p-7 border border-surface-border flex flex-col justify-between space-y-6">
            <div class="space-y-4">
              <div class="flex items-center justify-between">
                <span class="text-xs font-mono uppercase tracking-wider font-bold text-brand-400">Personal Vault</span>
                <span class="text-[10px] px-2 py-0.5 rounded bg-surface-elevated border border-surface-border text-slate-400">Single User</span>
              </div>
              <div class="flex items-baseline space-x-1">
                <span class="text-3xl sm:text-4xl font-extrabold text-white">
                  ₹{{ billingInterval === 'yearly' ? '1,999' : '199' }}
                </span>
                <span class="text-xs text-slate-400 font-medium">
                  / {{ billingInterval === 'yearly' ? 'year' : 'month' }}
                </span>
              </div>
              <p class="text-xs text-slate-400">
                Ideal for individuals, photographers, and developers seeking private, unmonitored backups.
              </p>

              <div class="pt-4 border-t border-surface-border space-y-2.5 text-xs text-slate-300">
                <div class="flex items-center space-x-2.5">
                  <CheckCircle2 class="w-4 h-4 text-accent-emerald shrink-0" />
                  <span><strong>200 GB</strong> zero-knowledge storage</span>
                </div>
                <div class="flex items-center space-x-2.5">
                  <CheckCircle2 class="w-4 h-4 text-accent-emerald shrink-0" />
                  <span>10 GB maximum per-file upload</span>
                </div>
                <div class="flex items-center space-x-2.5">
                  <CheckCircle2 class="w-4 h-4 text-accent-emerald shrink-0" />
                  <span>30-day automatic file version retention</span>
                </div>
                <div class="flex items-center space-x-2.5">
                  <CheckCircle2 class="w-4 h-4 text-accent-emerald shrink-0" />
                  <span>End-to-end encrypted link sharing</span>
                </div>
              </div>
            </div>

            <button
              @click="selectPlan('personal')"
              class="w-full btn-primary py-3 rounded-xl text-xs font-semibold text-white flex items-center justify-center space-x-2"
            >
              <span>Select Personal Plan</span>
              <ArrowRight class="w-3.5 h-3.5" />
            </button>
          </div>

          <!-- Business Plan -->
          <div class="vault-panel rounded-2xl p-7 border border-brand-500/30 bg-surface-card flex flex-col justify-between space-y-6 relative">
            <div class="absolute -top-3 right-6 px-2.5 py-0.5 rounded-full bg-brand-600 text-[10px] font-bold text-white tracking-wide uppercase shadow-sm">
              Popular for Teams
            </div>

            <div class="space-y-4">
              <div class="flex items-center justify-between">
                <span class="text-xs font-mono uppercase tracking-wider font-bold text-brand-400">Business Vault</span>
                <span class="text-[10px] px-2 py-0.5 rounded bg-surface-elevated border border-surface-border text-slate-400">Teams & Power Users</span>
              </div>
              <div class="flex items-baseline space-x-1">
                <span class="text-3xl sm:text-4xl font-extrabold text-white">
                  ₹{{ billingInterval === 'yearly' ? '4,999' : '499' }}
                </span>
                <span class="text-xs text-slate-400 font-medium">
                  / {{ billingInterval === 'yearly' ? 'year' : 'month' }}
                </span>
              </div>
              <p class="text-xs text-slate-400">
                Massive storage volume with enterprise compliance, audit logs, and extended retention.
              </p>

              <div class="pt-4 border-t border-surface-border space-y-2.5 text-xs text-slate-300">
                <div class="flex items-center space-x-2.5">
                  <CheckCircle2 class="w-4 h-4 text-accent-emerald shrink-0" />
                  <span><strong>2 TB (2,048 GB)</strong> zero-knowledge storage</span>
                </div>
                <div class="flex items-center space-x-2.5">
                  <CheckCircle2 class="w-4 h-4 text-accent-emerald shrink-0" />
                  <span>50 GB maximum per-file upload</span>
                </div>
                <div class="flex items-center space-x-2.5">
                  <CheckCircle2 class="w-4 h-4 text-accent-emerald shrink-0" />
                  <span>90-day automatic file version history</span>
                </div>
                <div class="flex items-center space-x-2.5">
                  <CheckCircle2 class="w-4 h-4 text-accent-emerald shrink-0" />
                  <span>Tamper-evident audit logging & priority support</span>
                </div>
              </div>
            </div>

            <button
              @click="selectPlan('business')"
              class="w-full btn-primary py-3 rounded-xl text-xs font-semibold text-white flex items-center justify-center space-x-2"
            >
              <span>Select Business Plan</span>
              <ArrowRight class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <!-- Payment Support Row -->
        <div class="mt-10 p-4 rounded-xl bg-surface-card border border-surface-border flex flex-col sm:flex-row items-center justify-between text-xs text-slate-400">
          <div class="flex items-center space-x-2 mb-2 sm:mb-0">
            <ShieldCheck class="w-4 h-4 text-brand-400" />
            <span>Securely processed via Razorpay • 100% Tax Invoice & GST Compliant</span>
          </div>
          <div class="font-mono text-[11px] text-slate-400">
            UPI • Cards (Visa / Mastercard / RuPay) • Netbanking
          </div>
        </div>
      </div>
    </section>

    <!-- Comparison Table -->
    <section class="py-20 border-b border-surface-border">
      <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center max-w-xl mx-auto space-y-3 mb-12">
          <h2 class="text-2xl font-extrabold text-white">How SpeedCloud compares</h2>
          <p class="text-xs text-slate-400">We don't scan your files to train machine learning models.</p>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead>
              <tr class="border-b border-surface-border text-slate-400 font-mono text-[11px]">
                <th class="py-3 px-4">Feature</th>
                <th class="py-3 px-4 text-white font-bold bg-surface-card rounded-t-lg">SpeedCloud</th>
                <th class="py-3 px-4">Google Drive</th>
                <th class="py-3 px-4">Proton Drive</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-surface-border text-slate-300">
              <tr>
                <td class="py-3.5 px-4 font-medium text-white">Zero-Knowledge (Client Derivation)</td>
                <td class="py-3.5 px-4 bg-surface-card font-bold text-accent-emerald">Yes (Argon2id)</td>
                <td class="py-3.5 px-4 text-slate-500">No (Server has keys)</td>
                <td class="py-3.5 px-4 text-slate-300">Yes (OpenPGP)</td>
              </tr>
              <tr>
                <td class="py-3.5 px-4 font-medium text-white">Direct-to-Storage Multipart (No Proxy)</td>
                <td class="py-3.5 px-4 bg-surface-card font-bold text-accent-emerald">Yes (S3/R2 Presigned)</td>
                <td class="py-3.5 px-4 text-slate-500">Proxied</td>
                <td class="py-3.5 px-4 text-slate-500">Proxied via Switzerland</td>
              </tr>
              <tr>
                <td class="py-3.5 px-4 font-medium text-white">Native Razorpay UPI & RuPay</td>
                <td class="py-3.5 px-4 bg-surface-card font-bold text-accent-emerald">Yes (Instant UPI)</td>
                <td class="py-3.5 px-4 text-slate-500">Cards only</td>
                <td class="py-3.5 px-4 text-slate-500">International Forex</td>
              </tr>
              <tr>
                <td class="py-3.5 px-4 font-medium text-white">200 GB Pricing</td>
                <td class="py-3.5 px-4 bg-surface-card font-bold text-brand-400">₹199 / mo</td>
                <td class="py-3.5 px-4 text-slate-400">₹210 / mo</td>
                <td class="py-3.5 px-4 text-slate-400">~₹400 / mo (€4)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- FAQ Accordion -->
    <section id="faq" class="py-20 border-b border-surface-border">
      <div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        <div class="text-center space-y-2 mb-10">
          <h2 class="text-2xl font-extrabold text-white">Frequently Asked Questions</h2>
          <p class="text-xs text-slate-400">Clear answers about our zero-knowledge technology and subscriptions.</p>
        </div>

        <div class="space-y-3">
          <div
            v-for="(faq, idx) in faqs"
            :key="idx"
            class="vault-panel rounded-xl overflow-hidden border border-surface-border transition-all"
          >
            <button
              @click="toggleFaq(idx)"
              class="w-full px-5 py-4 text-left flex items-center justify-between text-xs font-semibold text-white hover:bg-surface-card/60 transition-colors"
            >
              <span>{{ faq.q }}</span>
              <ChevronDown
                class="w-4 h-4 text-slate-400 transition-transform duration-200 shrink-0 ml-3"
                :class="{ 'rotate-180 text-brand-400': openFaqIndex === idx }"
              />
            </button>
            <div
              v-if="openFaqIndex === idx"
              class="px-5 pb-4 text-xs text-slate-400 leading-relaxed border-t border-surface-border/40 pt-3"
            >
              {{ faq.a }}
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="py-10 bg-surface-ground">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-4">
        <div class="flex items-center space-x-2">
          <div class="w-6 h-6 rounded bg-brand-600 flex items-center justify-center text-white">
            <Lock class="w-3.5 h-3.5" />
          </div>
          <span class="font-bold text-white">SpeedCloud</span>
          <span>© 2026. All rights reserved.</span>
        </div>
        <div class="flex items-center space-x-6 text-slate-400">
          <router-link to="/security" class="hover:text-white transition-colors">Security Whitepaper</router-link>
          <router-link to="/legal" class="hover:text-white transition-colors">Privacy & Terms</router-link>
          <router-link to="/pricing" class="hover:text-white transition-colors">Pricing</router-link>
        </div>
      </div>
    </footer>
  </div>
</template>
