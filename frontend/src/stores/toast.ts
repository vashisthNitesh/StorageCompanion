import { defineStore } from "pinia";
import { ref } from "vue";

export interface Toast {
  id: number;
  tone: "success" | "error" | "info";
  message: string;
}

export const useToastStore = defineStore("toast", () => {
  const toasts = ref<Toast[]>([]);
  let seq = 0;

  function push(message: string, tone: Toast["tone"] = "info", ms = 4500) {
    const id = ++seq;
    toasts.value = [...toasts.value.slice(-3), { id, tone, message }];
    setTimeout(() => dismiss(id), ms);
  }

  function dismiss(id: number) {
    toasts.value = toasts.value.filter((t) => t.id !== id);
  }

  return {
    toasts,
    success: (m: string) => push(m, "success"),
    error: (m: string) => push(m, "error", 7000),
    info: (m: string) => push(m, "info"),
    dismiss,
  };
});
