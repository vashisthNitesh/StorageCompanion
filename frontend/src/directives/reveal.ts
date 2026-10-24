import type { Directive } from "vue";

// v-reveal: fades and lifts an element in the first time it scrolls into view.
// The value is an optional delay in ms for staggering siblings. Content stays
// visible when motion is reduced or IntersectionObserver is unavailable.
type RevealEl = HTMLElement & { _reveal?: IntersectionObserver };

export const vReveal: Directive<RevealEl, number | undefined> = {
  mounted(el, binding) {
    if (typeof IntersectionObserver === "undefined" || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    el.classList.add("reveal");
    if (binding.value) el.style.transitionDelay = `${binding.value}ms`;
    el._reveal = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        el.classList.add("reveal-in");
        el._reveal?.disconnect();
      },
      { rootMargin: "0px 0px -8% 0px" }
    );
    el._reveal.observe(el);
  },
  unmounted(el) {
    el._reveal?.disconnect();
  },
};
