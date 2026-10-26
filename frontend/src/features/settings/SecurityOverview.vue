<script setup lang="ts">
import { computed } from "vue";
import { ShieldCheck, ShieldAlert, Check, AlertTriangle, LockKeyhole, KeyRound, LifeBuoy, Smartphone, MonitorSmartphone } from "lucide-vue-next";
import UiButton from "../../components/ui/UiButton.vue";
import { useAuthStore } from "../../stores/auth";
import { formatDate } from "../../lib/format";

// Summary at the top of the Security page: what's protecting the account and what to do next.
const props = defineProps<{ deviceCount: number | null }>();
const emit = defineEmits<{ setupTwoStep: []; jump: [id: string] }>();
const authStore = useAuthStore();
const user = computed(() => authStore.user);
const googleOnly = computed(() => !!user.value?.has_google && !user.value?.wrapped_master_key);

const checks = computed(() => [
  {
    icon: LockKeyhole,
    title: "End-to-end encryption",
    detail: "Files and names are encrypted on your device before upload.",
    ok: true,
  },
  googleOnly.value
    ? { icon: KeyRound, title: "Signed in with Google", detail: "Your Google account protects sign-in.", ok: true }
    : { icon: KeyRound, title: "Password", detail: "Also unlocks your encryption key.", ok: true, action: { label: "Change", run: () => emit("jump", "password") } },
  ...(user.value?.wrapped_master_key
    ? [
        user.value.has_recovery_key
          ? { icon: LifeBuoy, title: "Recovery key", detail: "Lets you reset your password and keep your files.", ok: true }
          : { icon: LifeBuoy, title: "No recovery key", detail: "Forgetting your password would lock you out of your files.", ok: false, action: { label: "Set up", primary: true, run: () => emit("jump", "recovery-key") } },
      ]
    : []),
  user.value?.mfa_enabled
    ? { icon: Smartphone, title: "Two-step verification", detail: "A code is needed after signing in.", ok: true }
    : { icon: Smartphone, title: "Two-step verification is off", detail: "Add a code from your phone so a stolen password isn't enough.", ok: false, action: { label: "Turn on", primary: true, run: () => emit("setupTwoStep") } },
  {
    icon: MonitorSmartphone,
    title: props.deviceCount === null ? "Signed-in devices" : `${props.deviceCount} signed-in ${props.deviceCount === 1 ? "device" : "devices"}`,
    detail: "Sign out anything you don't recognise.",
    ok: true,
    action: { label: "Review", run: () => emit("jump", "devices") },
  },
]);
const score = computed(() => checks.value.filter((c) => c.ok).length);
const allGood = computed(() => score.value === checks.value.length);
</script>

<template>
  <section class="overflow-hidden rounded-xl border border-line bg-surface shadow-xs" aria-labelledby="security-overview">
    <div class="grid lg:grid-cols-[300px_minmax(0,1fr)]">
      <div
        class="relative flex items-center gap-4 overflow-hidden p-5 lg:flex-col lg:items-start lg:justify-center lg:p-6"
        :class="allGood ? 'bg-success-soft/60' : 'bg-warning-soft/60'"
      >
        <div class="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full opacity-40 blur-2xl" :class="allGood ? 'bg-success/30' : 'bg-warning/30'" aria-hidden="true" />
        <span class="relative flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl shadow-sm ring-4" :class="allGood ? 'bg-success text-white ring-success/20' : 'bg-warning text-white ring-warning/20'">
          <component :is="allGood ? ShieldCheck : ShieldAlert" :size="28" :stroke-width="1.75" aria-hidden="true" />
        </span>
        <div class="relative">
          <h2 id="security-overview" class="text-lg font-semibold text-fg">{{ allGood ? "Your account is well protected" : (checks.length - score === 1 ? "One step left to secure your account" : `${checks.length - score} steps left to secure your account`) }}</h2>
          <p class="tabular mt-1 text-base text-fg-muted">{{ score }} of {{ checks.length }} protections on<template v-if="user?.created_at"> · member since {{ formatDate(user.created_at) }}</template></p>
        </div>
      </div>
      <ul class="divide-y divide-line">
        <li v-for="c in checks" :key="c.title" class="flex items-center gap-3 px-5 py-3.5">
          <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg" :class="c.ok ? 'bg-canvas-subtle text-fg-muted' : 'bg-warning-soft text-warning'">
            <component :is="c.icon" :size="18" :stroke-width="1.75" aria-hidden="true" />
          </span>
          <div class="min-w-0 flex-1">
            <p class="text-base font-medium text-fg">{{ c.title }}</p>
            <p class="text-sm text-fg-muted">{{ c.detail }}</p>
          </div>
          <UiButton v-if="c.action" size="sm" :variant="'primary' in c.action && c.action.primary ? 'primary' : 'ghost'" @click="c.action.run()">{{ c.action.label }}</UiButton>
          <span class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full" :class="c.ok ? 'bg-success-soft text-success' : 'bg-warning-soft text-warning'">
            <Check v-if="c.ok" :size="14" :stroke-width="2.5" aria-label="On" />
            <AlertTriangle v-else :size="13" :stroke-width="2.25" aria-label="Needs attention" />
          </span>
        </li>
      </ul>
    </div>
  </section>
</template>
