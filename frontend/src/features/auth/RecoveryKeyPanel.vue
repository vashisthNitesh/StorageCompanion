<script setup lang="ts">
import { ref } from "vue";
import { Copy, Check, Download, KeyRound } from "lucide-vue-next";
import UiButton from "../../components/ui/UiButton.vue";
import UiCheckbox from "../../components/ui/UiCheckbox.vue";
import { toast } from "../../lib/toast";

// Shows a recovery key once, with Copy / Download, and holds the "I've saved it" confirmation.
const props = defineProps<{ recoveryKey: string; email?: string }>();
const saved = defineModel<boolean>("saved", { default: false });
const copied = ref(false);

async function copy() {
  try {
    await navigator.clipboard.writeText(props.recoveryKey);
    copied.value = true;
    setTimeout(() => (copied.value = false), 2000);
  } catch {
    toast.error("Couldn't copy. Select the key and copy it yourself.");
  }
}

function download() {
  const text = [
    "SmartSpace recovery key",
    "",
    props.recoveryKey,
    "",
    ...(props.email ? [`Account: ${props.email}`] : []),
    `Created: ${new Date().toLocaleString()}`,
    "",
    "Use this key to choose a new password without losing your files.",
    "Anyone with this key and access to your email can reset your password, so keep it somewhere safe.",
  ].join("\n");
  const url = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = "smartspace-recovery-key.txt";
  a.click();
  URL.revokeObjectURL(url);
}
</script>

<template>
  <div class="space-y-4">
    <div class="rounded-lg border border-line bg-canvas-subtle p-4">
      <p class="flex items-center gap-2 text-sm font-medium text-fg-muted">
        <KeyRound :size="15" class="text-primary" aria-hidden="true" />Your recovery key
      </p>
      <p class="mt-2 select-all break-words font-mono text-md font-semibold tracking-wider text-fg" data-testid="recovery-key">{{ recoveryKey }}</p>
      <div class="mt-3 flex flex-wrap gap-2">
        <UiButton size="sm" :icon="copied ? Check : Copy" @click="copy">{{ copied ? "Copied" : "Copy" }}</UiButton>
        <UiButton size="sm" :icon="Download" @click="download">Download</UiButton>
      </div>
    </div>
    <p class="text-base text-fg-muted">
      If you forget your password, this key lets you choose a new one and keep your files. We can't see it or show it again, so store it in a password
      manager or print it.
    </p>
    <div class="rounded-lg bg-warning-soft p-3">
      <UiCheckbox v-model="saved" label="I've saved my recovery key" description="Without it, a forgotten password means losing access to your files." />
    </div>
  </div>
</template>
