import { onMounted, onUnmounted } from "vue";

export interface Shortcut {
  /** e.g. "mod+k", "u", "shift+?", "f2", "delete", "escape" */
  keys: string;
  handler: (e: KeyboardEvent) => void;
  /** Also fire while typing in a text field (only for mod+ combos). */
  allowInInputs?: boolean;
}

function isTyping(e: KeyboardEvent) {
  const el = e.target as HTMLElement | null;
  if (!el) return false;
  return el.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName) || el.getAttribute("role") === "combobox";
}

function matches(e: KeyboardEvent, combo: string) {
  const parts = combo.toLowerCase().split("+");
  const key = parts.pop()!;
  const wantMod = parts.includes("mod");
  const wantShift = parts.includes("shift");
  const mod = e.metaKey || e.ctrlKey;
  if (wantMod !== mod) return false;
  if (wantShift && !e.shiftKey) return false;
  if (e.altKey) return false;
  const pressed = e.key.toLowerCase();
  return pressed === key || (key === "delete" && pressed === "backspace" && (e.metaKey || !mod));
}

/** Registers keyboard shortcuts for the lifetime of the calling component. */
export function useShortcuts(shortcuts: () => Shortcut[]) {
  function onKey(e: KeyboardEvent) {
    if (e.defaultPrevented) return;
    // Don't steal keys from open dialogs/menus (Reka marks the body when modal).
    const modalOpen = !!document.querySelector('[role="dialog"][data-state="open"], [role="menu"][data-state="open"]');
    for (const s of shortcuts()) {
      if (!matches(e, s.keys)) continue;
      const typing = isTyping(e);
      if (typing && !(s.allowInInputs && s.keys.startsWith("mod+"))) continue;
      if (modalOpen && !s.keys.startsWith("mod+")) continue;
      e.preventDefault();
      s.handler(e);
      return;
    }
  }
  onMounted(() => window.addEventListener("keydown", onKey));
  onUnmounted(() => window.removeEventListener("keydown", onKey));
}
