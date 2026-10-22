import { onMounted, onUnmounted, ref } from "vue";

export function useMediaQuery(query: string) {
  const matches = ref(typeof window !== "undefined" && window.matchMedia(query).matches);
  let mq: MediaQueryList | null = null;
  const update = () => (matches.value = !!mq?.matches);
  onMounted(() => {
    mq = window.matchMedia(query);
    update();
    mq.addEventListener("change", update);
  });
  onUnmounted(() => mq?.removeEventListener("change", update));
  return matches;
}

export const isMac = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform);
export const modKey = isMac ? "⌘" : "Ctrl";
