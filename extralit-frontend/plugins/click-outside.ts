import { onClickOutside } from "@vueuse/core";
import { defineNuxtPlugin } from "#app";

type Handler = (event: Event) => void;

// Reimplements the `v-click-outside` directive (was the `v-click-outside` package)
// on top of @vueuse/core. Supports both `v-click-outside="fn"` and
// `v-click-outside="{ handler }"`. Consumer call sites are unchanged.
export default defineNuxtPlugin((nuxtApp) => {
  const stops = new WeakMap<HTMLElement, () => void>();

  const resolve = (value: Handler | { handler?: Handler } | undefined): Handler | undefined =>
    typeof value === "function" ? value : value?.handler;

  nuxtApp.vueApp.directive("click-outside", {
    mounted(el: HTMLElement, binding) {
      const handler = resolve(binding.value);
      if (handler) stops.set(el, onClickOutside(el, (event) => handler(event)));
    },
    unmounted(el: HTMLElement) {
      stops.get(el)?.();
      stops.delete(el);
    },
  });
});
