<script setup lang="ts">
import { ref, watch } from "vue";
import UiModal from "../../components/ui/UiModal.vue";
import UiButton from "../../components/ui/UiButton.vue";
import UiRadioGroup from "../../components/ui/UiRadioGroup.vue";
import UiCheckbox from "../../components/ui/UiCheckbox.vue";
import { conflictState, settleConflict, type ConflictChoice } from "../../lib/conflictPrompt";

const choice = ref<ConflictChoice>("keep-both");
const applyToAll = ref(false);
watch(
  () => conflictState.open,
  (o) => {
    if (o) {
      choice.value = "keep-both";
      applyToAll.value = false;
    }
  }
);
const options = [
  { value: "replace", label: "Replace", description: "Upload as a new version. The current version stays in version history." },
  { value: "keep-both", label: "Keep both", description: "Upload with a new name, like “photo (1).jpg”." },
  { value: "skip", label: "Skip", description: "Don't upload this file." },
];
</script>

<template>
  <UiModal
    :open="conflictState.open"
    title="A file with this name already exists"
    :description="`“${conflictState.fileName}” is already in ${conflictState.folderName}.`"
    size="md"
    @update:open="(o) => !o && settleConflict(null)"
  >
    <div class="space-y-5">
      <UiRadioGroup v-model="choice" label="What should happen?" :options="options" />
      <UiCheckbox
        v-if="conflictState.remaining > 1"
        v-model="applyToAll"
        :label="`Do this for all ${conflictState.remaining} files with the same name`"
      />
    </div>
    <template #footer>
      <UiButton @click="settleConflict(null)">Cancel upload</UiButton>
      <UiButton variant="primary" @click="settleConflict({ choice, applyToAll: applyToAll as boolean })">Continue</UiButton>
    </template>
  </UiModal>
</template>
