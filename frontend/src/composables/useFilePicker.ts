import { inject, provide, type InjectionKey } from "vue";

export interface FilePicker {
  pickFiles: () => void;
  pickFolder: () => void;
}

const KEY: InjectionKey<FilePicker> = Symbol("file-picker");

export function provideFilePicker(picker: FilePicker) {
  provide(KEY, picker);
}

export function useFilePicker(): FilePicker {
  const picker = inject(KEY);
  if (!picker) throw new Error("useFilePicker must be used inside AppLayout");
  return picker;
}
