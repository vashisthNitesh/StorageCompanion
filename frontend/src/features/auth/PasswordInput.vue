<script setup lang="ts">
import { ref } from "vue";
import { Eye, EyeOff } from "lucide-vue-next";

const model = defineModel<string>({ required: true });
defineProps<{ id: string; autocomplete?: string; placeholder?: string; required?: boolean; minlength?: number }>();
const visible = ref(false);
</script>

<template>
  <div class="relative">
    <input
      :id="id"
      v-model="model"
      :type="visible ? 'text' : 'password'"
      :autocomplete="autocomplete"
      :placeholder="placeholder"
      :required="required"
      :minlength="minlength"
      class="input pr-11"
    />
    <button
      type="button"
      class="absolute right-1 top-1/2 -translate-y-1/2 icon-btn h-8 w-8"
      :aria-label="visible ? 'Hide password' : 'Show password'"
      :title="visible ? 'Hide password' : 'Show password'"
      @click="visible = !visible"
    >
      <EyeOff v-if="visible" class="h-4 w-4" />
      <Eye v-else class="h-4 w-4" />
    </button>
  </div>
</template>
