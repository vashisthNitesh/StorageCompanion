<script setup lang="ts">
import { ref } from "vue";
import { Eye, EyeOff, ArrowBigUp } from "lucide-vue-next";
import UiInput from "./UiInput.vue";
import UiButton from "./UiButton.vue";

defineOptions({ inheritAttrs: false });
const model = defineModel<string>({ default: "" });
defineProps<{ invalid?: boolean; size?: "sm" | "md" | "lg"; id?: string }>();
const visible = ref(false);
const capsLock = ref(false);
const input = ref<InstanceType<typeof UiInput> | null>(null);

function trackCaps(e: KeyboardEvent) {
  capsLock.value = typeof e.getModifierState === "function" && e.getModifierState("CapsLock");
}
defineExpose({ focus: () => input.value?.focus() });
</script>

<template>
  <div>
    <UiInput
      ref="input"
      v-model="model"
      v-bind="$attrs"
      :id="id"
      :type="visible ? 'text' : 'password'"
      :invalid="invalid"
      :size="size"
      spellcheck="false"
      autocapitalize="off"
      @keydown="trackCaps"
      @keyup="trackCaps"
      @blur="capsLock = false"
    >
      <template #trailing>
        <UiButton
          variant="ghost"
          size="sm"
          icon-only
          :icon="visible ? EyeOff : Eye"
          :aria-label="visible ? 'Hide password' : 'Show password'"
          :aria-pressed="visible"
          @click="visible = !visible"
        />
      </template>
    </UiInput>
    <p v-if="capsLock" class="mt-1.5 flex items-center gap-1.5 text-sm text-warning" role="status">
      <ArrowBigUp :size="14" :stroke-width="2" aria-hidden="true" /> Caps Lock is on
    </p>
  </div>
</template>
