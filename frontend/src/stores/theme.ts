import { defineStore } from "pinia";
import { ref, watch } from "vue";

export type ThemePreference = "light" | "dark" | "system";
const STORAGE_KEY = "sc_theme";

function readPreference(): ThemePreference {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return value === "light" || value === "dark" ? value : "system";
  } catch {
    return "system";
  }
}

/** Applies the preference to <html data-theme>. "system" removes the attribute so the
 *  prefers-color-scheme media query in tokens.css decides. */
export function applyTheme(pref: ThemePreference) {
  const root = document.documentElement;
  if (pref === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", pref);
}

export const useThemeStore = defineStore("theme", () => {
  const preference = ref<ThemePreference>(readPreference());
  watch(
    preference,
    (pref) => {
      applyTheme(pref);
      try {
        localStorage.setItem(STORAGE_KEY, pref);
      } catch {
        // storage unavailable
      }
    },
    { immediate: true }
  );
  return { preference };
});

// Apply before the app mounts to avoid a flash of the wrong theme.
applyTheme(readPreference());
