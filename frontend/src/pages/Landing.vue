<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import {
  Cloud,
  Zap,
  ShieldCheck,
  Smartphone,
  CreditCard,
  Lock,
  ArrowRight,
  CheckCircle2,
  HelpCircle,
  HardDrive,
  FileSearch,
  Key,
} from "lucide-vue-next";

const router = useRouter();
const billingInterval = ref<"monthly" | "yearly">("monthly");

function goToRegister(planCode: string = "personal") {
  router.push({ path: "/register", query: { plan: planCode, interval: billingInterval.value } });
}
</script>

<template>
  <div class="min-h-screen flex flex-col bg-[#070D1A] text-slate-100 selection:bg-brand-500 selection:text-white">
    <!-- Navbar -->
    <header class="sticky top-0 z-40 glass-panel border-b border-slate-800/80 bg-[#070D1A]/80">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
        <!-- Logo -->
        <router-link to="/" class="flex items-center space-x-3 group">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-accent-orange flex items-center justify-center shadow-lg shadow-brand-500/20 group-hover:scale-105 transition-transform">
            <Cloud class="w-6 h-6 text-white fill-white/20" />
          </div>
          <span class="text-2xl font-black tracking-tight text-white">
            Speed<span class="text-brand-400">Cloud</span>
          </span>
        </router-link>

        <!-- Nav Links -->
        <nav class="hidden md:flex items-center space-x-8 text-sm font-medium text-slate-300">
          <router-link to="/" class="text-brand-400 font-semibold">Home</router-link>
          <a href="#features" class="hover:text-white transition-colors">Features</a>
          <router-link to="/pricing" class="hover:text-white transition-colors">Pricing</router-link>
          <router-link to="/security" class="hover:text-white transition-colors">Security</router-link>
          <a href="#faq" class="hover:text-white transition-colors">FAQ</a>
        </nav>

        <!-- Actions -->
        <div class="flex items-center space-x-4">
          <router-link
            to="/login"
            class="px-4 py-2 text-sm font-medium text-slate-200 hover:text-white transition-colors"
          >
            Login
          </router-link>
          <button
            @click="goToRegister('personal')"
            class="px-5 py-2.5 rounded-xl text-sm font-semibold bg-brand-600 hover:bg-brand-500 text-white shadow-lg shadow-brand-600/30 hover:shadow-brand-500/50 transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            Get Started
          </button>
        </div>
      </div>
    </header>

    <!-- Hero Section -->
    <section class="relative pt-12 pb-20 overflow-hidden">
      <!-- Glow Background Elements -->
      <div class="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[450px] bg-brand-600/15 rounded-full blur-[120px] pointer-events-none"></div>
      <div class="absolute top-1/3 right-10 w-[400px] h-[300px] bg-accent-orange/10 rounded-full blur-[100px] pointer-events-none"></div>

      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div class="grid lg:grid-cols-12 gap-12 items-center">
          <!-- Hero Text -->
          <div class="lg:col-span-6 space-y-6 text-center lg:text-left">
            <div class="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-brand-950/80 border border-brand-800/60 text-xs font-semibold text-brand-300">
              <Zap class="w-3.5 h-3.5 text-accent-orange animate-pulse" />
              <span>India's Zero-Knowledge Cloud Storage</span>
            </div>

            <h1 class="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-[1.15]">
              India’s Fastest <br />
              <span class="bg-clip-text text-transparent bg-gradient-to-r from-brand-400 via-sky-300 to-accent-orange">
                Cloud Storage
              </span>
            </h1>

            <p class="text-lg text-slate-300 max-w-xl mx-auto lg:mx-0 font-normal leading-relaxed">
              Upload, Store & Access Your Files at Lightning Speed with Zero-Knowledge Client-Side Encryption. No operator surveillance. Zero egress fees.
            </p>

            <div class="flex flex-col sm:flex-row items-center justify-center lg:justify-start space-y-3 sm:space-y-0 sm:space-x-4 pt-2">
              <button
                @click="goToRegister('personal')"
                class="w-full sm:w-auto px-8 py-4 rounded-xl text-base font-bold bg-gradient-to-r from-accent-orange to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white shadow-xl shadow-orange-500/25 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center space-x-2"
              >
                <span>Get Started Now</span>
                <ArrowRight class="w-5 h-5" />
              </button>
              <button
                @click="goToRegister('business')"
                class="w-full sm:w-auto px-8 py-4 rounded-xl text-base font-bold bg-slate-800/90 hover:bg-slate-700/90 text-white border border-slate-700/80 transition-all hover:scale-[1.02] active:scale-[0.98]"
              >
                For Business
              </button>
            </div>

            <!-- Trust Badges -->
            <div class="pt-6 flex flex-wrap items-center justify-center lg:justify-start gap-6 text-xs text-slate-400">
              <div class="flex items-center space-x-2">
                <ShieldCheck class="w-4 h-4 text-emerald-400" />
                <span>AES-256-GCM End-to-End</span>
              </div>
              <div class="flex items-center space-x-2">
                <Zap class="w-4 h-4 text-brand-400" />
                <span>Direct-to-R2 (Zero Egress)</span>
              </div>
              <div class="flex items-center space-x-2">
                <Key class="w-4 h-4 text-accent-orange" />
                <span>24-Word Recovery Phrase</span>
              </div>
            </div>
          </div>

          <!-- Hero Mockup Illustration (Matching SpeedCloud Image) -->
          <div class="lg:col-span-6 relative flex justify-center">
            <div class="relative w-full max-w-lg rounded-3xl p-4 glass-card border border-brand-500/30 speed-glow bg-gradient-to-b from-[#0F1E36] to-[#0A1224]">
              <!-- Mockup Header -->
              <div class="flex items-center justify-between pb-3 mb-4 border-b border-slate-700/60">
                <div class="flex space-x-2">
                  <div class="w-3 h-3 rounded-full bg-rose-500/80"></div>
                  <div class="w-3 h-3 rounded-full bg-amber-500/80"></div>
                  <div class="w-3 h-3 rounded-full bg-emerald-500/80"></div>
                </div>
                <div class="px-3 py-1 rounded-md bg-slate-800/80 text-[11px] font-mono text-slate-400 flex items-center space-x-1.5">
                  <Lock class="w-3 h-3 text-emerald-400" />
                  <span>vault.speedcloud.app (Encrypted)</span>
                </div>
              </div>

              <!-- Speed Graphic inside Laptop / UI Frame -->
              <div class="space-y-4">
                <div class="p-6 rounded-2xl bg-[#080E1C] border border-slate-800 text-center relative overflow-hidden">
                  <div class="w-20 h-20 mx-auto rounded-full bg-brand-500/10 border-2 border-brand-400 flex items-center justify-center shadow-lg shadow-brand-500/30 mb-3">
                    <Cloud class="w-10 h-10 text-brand-400" />
                  </div>
                  <div class="text-2xl font-black text-white">450 MB/s</div>
                  <div class="text-xs text-brand-400 font-medium">Blazing Fast Multi-Part Direct Transfer</div>
                  <!-- Speed gauge curve representation -->
                  <div class="mt-4 w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                    <div class="bg-gradient-to-r from-brand-500 via-sky-400 to-accent-orange h-full w-[88%] rounded-full"></div>
                  </div>
                </div>

                <!-- Simulated File Row Transfer -->
                <div class="space-y-2">
                  <div class="flex items-center justify-between p-3 rounded-xl bg-slate-800/40 border border-slate-700/50 text-xs">
                    <div class="flex items-center space-x-3">
                      <div class="w-8 h-8 rounded-lg bg-brand-600/20 text-brand-400 flex items-center justify-center font-bold">
                        PDF
                      </div>
                      <div>
                        <div class="font-semibold text-slate-200">Financial_Audit_2026.pdf</div>
                        <div class="text-[10px] text-slate-400 font-mono">14.2 MB • Encrypted (AES-GCM)</div>
                      </div>
                    </div>
                    <span class="text-emerald-400 font-semibold">100% Uploaded</span>
                  </div>

                  <div class="flex items-center justify-between p-3 rounded-xl bg-slate-800/40 border border-slate-700/50 text-xs">
                    <div class="flex items-center space-x-3">
                      <div class="w-8 h-8 rounded-lg bg-accent-orange/20 text-accent-orange flex items-center justify-center font-bold">
                        MP4
                      </div>
                      <div>
                        <div class="font-semibold text-slate-200">Product_Demo_4K.mp4</div>
                        <div class="text-[10px] text-slate-400 font-mono">85.0 MB • Chunk 8/11</div>
                      </div>
                    </div>
                    <span class="text-brand-400 font-semibold">73% (48 MB/s)</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Why Choose SpeedCloud? Section (Matching Mockup 4 Cards) -->
    <section id="features" class="py-20 bg-[#091124] border-y border-slate-800/60">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center max-w-3xl mx-auto mb-16">
          <h2 class="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            Why Choose SpeedCloud?
          </h2>
          <p class="mt-4 text-base text-slate-300">
            Engineered with zero compromises: the convenience of modern cloud storage with total mathematical privacy.
          </p>
        </div>

        <div class="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          <!-- Card 1 -->
          <div class="p-6 rounded-2xl glass-card transition-all hover:-translate-y-1 space-y-4">
            <div class="w-12 h-12 rounded-xl bg-orange-500/10 border border-orange-500/30 text-accent-orange flex items-center justify-center">
              <Zap class="w-6 h-6" />
            </div>
            <h3 class="text-lg font-bold text-white">Blazing Fast Uploads</h3>
            <p class="text-sm text-slate-300 leading-relaxed">
              Upload files in seconds with ultra-fast multi-part streams direct to Cloudflare R2 edge locations.
            </p>
          </div>

          <!-- Card 2 -->
          <div class="p-6 rounded-2xl glass-card transition-all hover:-translate-y-1 space-y-4">
            <div class="w-12 h-12 rounded-xl bg-brand-500/10 border border-brand-500/30 text-brand-400 flex items-center justify-center">
              <ShieldCheck class="w-6 h-6" />
            </div>
            <h3 class="text-lg font-bold text-white">Secure & Encrypted</h3>
            <p class="text-sm text-slate-300 leading-relaxed">
              True zero-knowledge encryption: Argon2id KDF + AES-256-GCM. We cannot read your files even if compelled.
            </p>
          </div>

          <!-- Card 3 -->
          <div class="p-6 rounded-2xl glass-card transition-all hover:-translate-y-1 space-y-4">
            <div class="w-12 h-12 rounded-xl bg-sky-500/10 border border-sky-500/30 text-sky-400 flex items-center justify-center">
              <Smartphone class="w-6 h-6" />
            </div>
            <h3 class="text-lg font-bold text-white">Access Anywhere</h3>
            <p class="text-sm text-slate-300 leading-relaxed">
              Access your encrypted vault from any device or browser with responsive layout and client decryption.
            </p>
          </div>

          <!-- Card 4 -->
          <div class="p-6 rounded-2xl glass-card transition-all hover:-translate-y-1 space-y-4">
            <div class="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center">
              <CreditCard class="w-6 h-6" />
            </div>
            <h3 class="text-lg font-bold text-white">Affordable Plans</h3>
            <p class="text-sm text-slate-300 leading-relaxed">
              Pure subscription pricing in INR with zero hidden bandwidth or egress fees. Powered by Razorpay & UPI.
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- Pricing Section (Matching Mockup Cards) -->
    <section id="pricing" class="py-20 relative">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center max-w-3xl mx-auto mb-12">
          <h2 class="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            Flexible Plans for Everyone
          </h2>
          <p class="mt-3 text-slate-300 text-base">
            No ad-tracking, no free tier compromises. Pure private cloud storage.
          </p>

          <!-- Toggle -->
          <div class="mt-8 inline-flex items-center p-1.5 rounded-2xl bg-slate-900 border border-slate-800">
            <button
              @click="billingInterval = 'monthly'"
              class="px-5 py-2 rounded-xl text-sm font-semibold transition-all"
              :class="billingInterval === 'monthly' ? 'bg-brand-600 text-white shadow-md' : 'text-slate-400 hover:text-white'"
            >
              Monthly Billing
            </button>
            <button
              @click="billingInterval = 'yearly'"
              class="px-5 py-2 rounded-xl text-sm font-semibold transition-all flex items-center space-x-1.5"
              :class="billingInterval === 'yearly' ? 'bg-brand-600 text-white shadow-md' : 'text-slate-400 hover:text-white'"
            >
              <span>Annual Billing</span>
              <span class="px-2 py-0.5 rounded-full text-[10px] bg-accent-orange text-white font-bold">2 Months Free</span>
            </button>
          </div>
        </div>

        <!-- Pricing Cards -->
        <div class="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          <!-- Personal Plan (Matching Mockup Orange Action) -->
          <div class="rounded-3xl p-8 glass-card border border-slate-700/80 hover:border-brand-500/50 transition-all flex flex-col justify-between relative bg-gradient-to-b from-[#0F1C34] to-[#0A1224]">
            <div class="space-y-6">
              <div>
                <span class="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-brand-500/10 text-brand-400 border border-brand-500/30">
                  Personal Plan
                </span>
                <div class="mt-4 flex items-baseline space-x-2">
                  <span class="text-4xl sm:text-5xl font-extrabold text-white">
                    ₹{{ billingInterval === 'yearly' ? '1,999' : '199' }}
                  </span>
                  <span class="text-slate-400 font-medium">/ {{ billingInterval === 'yearly' ? 'year' : 'month' }}</span>
                </div>
                <p class="mt-2 text-xs text-slate-400">Perfect for individual privacy, personal archives, and secure documents.</p>
              </div>

              <div class="pt-4 border-t border-slate-800 space-y-3">
                <div class="flex items-center space-x-3 text-sm text-slate-200">
                  <CheckCircle2 class="w-5 h-5 text-brand-400 shrink-0" />
                  <span><strong>200 GB</strong> Encrypted Storage</span>
                </div>
                <div class="flex items-center space-x-3 text-sm text-slate-200">
                  <CheckCircle2 class="w-5 h-5 text-brand-400 shrink-0" />
                  <span>Blazing Fast Direct-to-R2 Uploads</span>
                </div>
                <div class="flex items-center space-x-3 text-sm text-slate-200">
                  <CheckCircle2 class="w-5 h-5 text-brand-400 shrink-0" />
                  <span>100% Zero-Knowledge Privacy</span>
                </div>
                <div class="flex items-center space-x-3 text-sm text-slate-200">
                  <CheckCircle2 class="w-5 h-5 text-brand-400 shrink-0" />
                  <span>Password-Protected Share Links</span>
                </div>
                <div class="flex items-center space-x-3 text-sm text-slate-200">
                  <CheckCircle2 class="w-5 h-5 text-brand-400 shrink-0" />
                  <span>30 Days Version History</span>
                </div>
              </div>
            </div>

            <div class="pt-8">
              <button
                @click="goToRegister('personal')"
                class="w-full py-4 rounded-xl font-bold text-white bg-gradient-to-r from-accent-orange to-amber-500 hover:from-orange-600 hover:to-amber-600 shadow-xl shadow-orange-500/20 transition-all hover:scale-[1.01] active:scale-[0.99]"
              >
                Get Started
              </button>
            </div>
          </div>

          <!-- Business Plan (Matching Mockup Blue Action) -->
          <div class="rounded-3xl p-8 glass-card border border-brand-500/40 shadow-xl shadow-brand-500/10 flex flex-col justify-between relative bg-gradient-to-b from-[#112344] to-[#0A1428]">
            <div class="absolute -top-3.5 right-8 px-3.5 py-1 rounded-full text-[11px] font-extrabold uppercase tracking-wider bg-brand-500 text-white shadow-md">
              Most Popular
            </div>

            <div class="space-y-6">
              <div>
                <span class="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-brand-500/20 text-brand-300 border border-brand-500/40">
                  Business Plan
                </span>
                <div class="mt-4 flex items-baseline space-x-2">
                  <span class="text-4xl sm:text-5xl font-extrabold text-white">
                    ₹{{ billingInterval === 'yearly' ? '4,999' : '499' }}
                  </span>
                  <span class="text-slate-400 font-medium">/ {{ billingInterval === 'yearly' ? 'year' : 'month' }}</span>
                </div>
                <p class="mt-2 text-xs text-slate-400">For high-throughput professionals, teams, and compliance-first power users.</p>
              </div>

              <div class="pt-4 border-t border-slate-800 space-y-3">
                <div class="flex items-center space-x-3 text-sm text-slate-200">
                  <CheckCircle2 class="w-5 h-5 text-brand-400 shrink-0" />
                  <span><strong>2 TB</strong> High-Speed Storage</span>
                </div>
                <div class="flex items-center space-x-3 text-sm text-slate-200">
                  <CheckCircle2 class="w-5 h-5 text-brand-400 shrink-0" />
                  <span>Team Access & X25519 Key Sharing</span>
                </div>
                <div class="flex items-center space-x-3 text-sm text-slate-200">
                  <CheckCircle2 class="w-5 h-5 text-brand-400 shrink-0" />
                  <span>Unlimited Connected Devices</span>
                </div>
                <div class="flex items-center space-x-3 text-sm text-slate-200">
                  <CheckCircle2 class="w-5 h-5 text-brand-400 shrink-0" />
                  <span>365 Days Extended Version Retention</span>
                </div>
                <div class="flex items-center space-x-3 text-sm text-slate-200">
                  <CheckCircle2 class="w-5 h-5 text-brand-400 shrink-0" />
                  <span>Priority 24/7 Dedicated Support</span>
                </div>
              </div>
            </div>

            <div class="pt-8">
              <button
                @click="goToRegister('business')"
                class="w-full py-4 rounded-xl font-bold text-white bg-brand-600 hover:bg-brand-500 shadow-xl shadow-brand-600/30 transition-all hover:scale-[1.01] active:scale-[0.99]"
              >
                Choose Plan
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Testimonial Section (Matching Mockup with Rajesh Kumar, Mumbai) -->
    <section class="py-16 bg-[#080E1C] border-t border-slate-800/60">
      <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <div class="glass-card rounded-3xl p-8 sm:p-12 relative border border-slate-700/60 max-w-2xl mx-auto">
          <div class="text-4xl text-brand-400 font-serif mb-4 leading-none">“</div>
          <p class="text-xl sm:text-2xl font-medium text-slate-100 italic leading-relaxed">
            SpeedCloud is incredibly fast and secure! Perfect for all my storage needs!
          </p>
          <div class="mt-8 flex items-center justify-center space-x-4">
            <div class="w-12 h-12 rounded-full overflow-hidden border-2 border-brand-400 shadow-md">
              <img
                src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?fit=crop&w=120&h=120&q=80"
                alt="Rajesh Kumar"
                class="w-full h-full object-cover"
              />
            </div>
            <div class="text-left">
              <div class="font-bold text-white text-base">Rajesh Kumar</div>
              <div class="text-xs text-brand-400">Mumbai, India</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Honest Comparison Matrix -->
    <section class="py-20 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="text-center max-w-3xl mx-auto mb-16">
        <h2 class="text-3xl font-extrabold text-white tracking-tight">
          How SpeedCloud Compares
        </h2>
        <p class="mt-3 text-slate-300 text-sm">
          Unlike legacy cloud providers, our architecture is physically incapable of scanning or selling your files.
        </p>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm text-slate-300 border-collapse">
          <thead>
            <tr class="border-b border-slate-800 text-xs font-bold uppercase text-slate-400">
              <th class="py-4 px-6">Capability</th>
              <th class="py-4 px-6 text-brand-400 font-extrabold text-base">SpeedCloud</th>
              <th class="py-4 px-6">Google Drive</th>
              <th class="py-4 px-6">Dropbox</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800/60 font-medium">
            <tr>
              <td class="py-4 px-6">Zero-Knowledge Content Encryption</td>
              <td class="py-4 px-6 text-emerald-400 font-bold">✓ Client AES-256-GCM</td>
              <td class="py-4 px-6 text-rose-400">✗ Provider holds keys</td>
              <td class="py-4 px-6 text-rose-400">✗ Provider holds keys</td>
            </tr>
            <tr>
              <td class="py-4 px-6">Encrypted File & Folder Names</td>
              <td class="py-4 px-6 text-emerald-400 font-bold">✓ Client-side ciphertext</td>
              <td class="py-4 px-6 text-rose-400">✗ Plaintext on server</td>
              <td class="py-4 px-6 text-rose-400">✗ Plaintext on server</td>
            </tr>
            <tr>
              <td class="py-4 px-6">Direct R2 Egress Fees</td>
              <td class="py-4 px-6 text-emerald-400 font-bold">✓ Zero Bandwidth Fees</td>
              <td class="py-4 px-6 text-slate-400">Throttled</td>
              <td class="py-4 px-6 text-slate-400">Bandwidth caps</td>
            </tr>
            <tr>
              <td class="py-4 px-6">Indian Rupee (INR / UPI) Checkout</td>
              <td class="py-4 px-6 text-emerald-400 font-bold">✓ Native Razorpay / UPI</td>
              <td class="py-4 px-6 text-slate-400">Credit card only</td>
              <td class="py-4 px-6 text-slate-400">USD conversions</td>
            </tr>
            <tr>
              <td class="py-4 px-6">Offline 24-Word Recovery Key</td>
              <td class="py-4 px-6 text-emerald-400 font-bold">✓ Hard cryptographic gate</td>
              <td class="py-4 px-6 text-rose-400">✗ No Master Key</td>
              <td class="py-4 px-6 text-rose-400">✗ No Master Key</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- FAQ Accordion -->
    <section id="faq" class="py-20 bg-[#091124] border-t border-slate-800/60">
      <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <h2 class="text-3xl font-extrabold text-white text-center mb-12">
          Frequently Asked Questions
        </h2>

        <div class="space-y-4">
          <details class="group p-6 rounded-2xl glass-card border border-slate-800 transition-colors">
            <summary class="flex justify-between items-center font-bold text-white cursor-pointer list-none">
              <span>Why is there no free tier?</span>
              <span class="text-brand-400 group-open:rotate-180 transition-transform">▼</span>
            </summary>
            <p class="mt-4 text-sm text-slate-300 leading-relaxed">
              When a cloud storage product is "free", your data is scanned, indexed, and leveraged for AI training or ad targeting. SpeedCloud is funded purely through honest, transparent subscriptions starting at just ₹199/month. We have zero interest in monetizing your data.
            </p>
          </details>

          <details class="group p-6 rounded-2xl glass-card border border-slate-800 transition-colors">
            <summary class="flex justify-between items-center font-bold text-white cursor-pointer list-none">
              <span>What happens if I forget my password?</span>
              <span class="text-brand-400 group-open:rotate-180 transition-transform">▼</span>
            </summary>
            <p class="mt-4 text-sm text-slate-300 leading-relaxed">
              Because SpeedCloud is zero-knowledge, our team cannot decrypt or reset your vault. When you register, you are given a 24-word cryptographic recovery phrase. If you ever forget your password, that 24-word phrase will unwrap your Master Key and restore all your files.
            </p>
          </details>

          <details class="group p-6 rounded-2xl glass-card border border-slate-800 transition-colors">
            <summary class="flex justify-between items-center font-bold text-white cursor-pointer list-none">
              <span>How fast are uploads and downloads?</span>
              <span class="text-brand-400 group-open:rotate-180 transition-transform">▼</span>
            </summary>
            <p class="mt-4 text-sm text-slate-300 leading-relaxed">
              Unlike traditional platforms where files proxy through an application server, SpeedCloud uploads encrypted chunks directly to Cloudflare R2's global edge network across 4 parallel TCP connections. This yields near wire-speed throughput.
            </p>
          </details>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="py-12 border-t border-slate-800 bg-[#060B16] text-slate-400 text-xs">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-6">
        <div class="flex items-center space-x-3">
          <div class="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
            <Cloud class="w-5 h-5 text-white" />
          </div>
          <span class="font-bold text-white text-sm">SpeedCloud Storage</span>
          <span>© 2026 SpeedCloud Technologies Private Limited.</span>
        </div>
        <div class="flex items-center space-x-6">
          <router-link to="/pricing" class="hover:text-white">Pricing</router-link>
          <router-link to="/security" class="hover:text-white">Security Architecture</router-link>
          <router-link to="/legal" class="hover:text-white">Privacy Policy & Terms</router-link>
        </div>
      </div>
    </footer>
  </div>
</template>
