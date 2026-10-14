import { defineNuxtPlugin } from "#app";
import { loadDependencyContainer } from "~/v1/di";

// Registers the ts-injecty container. Ordered last (3.) so $auth (1.) and $axios (2.)
// are available when repositories resolve.
export default defineNuxtPlugin((nuxtApp) => {
  loadDependencyContainer(nuxtApp as never);
});
