<script setup lang="ts">
import { computed } from "vue";
import { Download } from "lucide-vue-next";
import UiButton from "../../../components/ui/UiButton.vue";
import type { FileNode } from "../../../stores/files";
import { kindInfo, kindOf } from "../../files/fileTypes";
import { extensionOf } from "../previewTypes";
import type { ViewProblem } from "./types";

const props = defineProps<{ node: FileNode; problem: ViewProblem }>();
const emit = defineEmits<{ download: [] }>();

const copy = computed(() => {
  const ext = extensionOf(props.node.name).toUpperCase();
  switch (props.problem.kind) {
    case "too-large":
      return { title: "This file is too large to preview", text: "Download it to open it on your device." };
    case "damaged":
      return { title: "This file couldn't be decrypted", text: "It may be damaged. Try downloading it, or upload it again." };
    case "locked":
      return { title: "Your files are locked", text: "Sign in again to unlock your files, then open this one." };
    case "failed":
      return { title: "Couldn't open this file", text: props.problem.message };
    default:
      return {
        title: ext ? `No preview for ${ext} files` : "No preview for this file",
        text: "This browser can't display it. Download it to open it in another app.",
      };
  }
});
</script>

<template>
  <div class="flex h-full items-center justify-center p-6">
    <div class="max-w-sm text-center">
      <span class="mx-auto flex h-20 w-20 items-center justify-center rounded-xl" :class="kindInfo(kindOf(node)).tint">
        <component :is="kindInfo(kindOf(node)).icon" :size="40" :stroke-width="1.25" aria-hidden="true" />
      </span>
      <h2 class="mt-5 text-md font-semibold text-fg">{{ copy.title }}</h2>
      <p class="mt-1.5 text-base text-fg-muted">{{ copy.text }}</p>
      <UiButton v-if="problem.kind !== 'locked'" class="mt-6" variant="primary" :icon="Download" @click="emit('download')">Download</UiButton>
    </div>
  </div>
</template>
