<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import UiModal from "../../components/ui/UiModal.vue";
import UiButton from "../../components/ui/UiButton.vue";
import UiFormField from "../../components/ui/UiFormField.vue";
import UiInput from "../../components/ui/UiInput.vue";
import UiAlert from "../../components/ui/UiAlert.vue";
import { useForm } from "../../composables/useForm";
import { validateName } from "./nameValidation";

const open = defineModel<boolean>("open", { default: false });
const props = defineProps<{
  mode: "create" | "rename";
  type: "file" | "folder";
  initial?: string;
  parentId: string | null;
  exceptId?: string;
  submit: (name: string) => Promise<unknown>;
}>();

const form = useForm({ name: "" }, { name: [(v: string) => validateName(v, { parentId: props.parentId, exceptId: props.exceptId, type: props.type })] });
const input = ref<InstanceType<typeof UiInput> | null>(null);

watch(open, async (o) => {
  if (!o) return;
  form.reset({ name: props.initial ?? (props.mode === "create" ? "Untitled folder" : "") });
  await nextTick();
  setTimeout(() => {
    const el = input.value?.el as HTMLInputElement | undefined;
    if (!el) return;
    el.focus();
    const dot = props.type === "file" ? el.value.lastIndexOf(".") : -1;
    el.setSelectionRange(0, dot > 0 ? dot : el.value.length);
  }, 30);
});

async function save() {
  const ok = await form.submit((v) => props.submit(v.name.trim()));
  if (ok) open.value = false;
}
</script>

<template>
  <UiModal v-model:open="open" :title="mode === 'create' ? 'New folder' : `Rename ${type}`" size="sm" :dismissible="!form.submitting.value">
    <form :ref="(el) => (form.formEl.value = el as HTMLFormElement)" novalidate class="space-y-4" @submit.prevent="save">
      <UiFormField :label="mode === 'create' ? 'Folder name' : 'Name'" :error="form.errors.name">
        <UiInput ref="input" v-model="form.values.name" autocomplete="off" maxlength="300" @blur="form.blur('name')" />
      </UiFormField>
      <UiAlert v-if="form.formError.value">{{ form.formError.value }}</UiAlert>
      <button type="submit" class="hidden" tabindex="-1" aria-hidden="true" />
    </form>
    <template #footer>
      <UiButton :disabled="form.submitting.value" @click="open = false">Cancel</UiButton>
      <UiButton variant="primary" :loading="form.submitting.value" @click="save">{{ mode === "create" ? "Create folder" : "Rename" }}</UiButton>
    </template>
  </UiModal>
</template>
