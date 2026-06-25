import { defineNuxtPlugin } from "#app";
import BaseSvgIcon from "~/components/base/BaseSvgIcon.vue";

// Register the custom icon component under every name the codebase already uses
// for vue-svgicon's <svgicon>, so the ~77 call sites stay unchanged.
export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.vueApp.component("svgicon", BaseSvgIcon);
  nuxtApp.vueApp.component("SvgIcon", BaseSvgIcon);
  nuxtApp.vueApp.component("svg-icon", BaseSvgIcon);
});
