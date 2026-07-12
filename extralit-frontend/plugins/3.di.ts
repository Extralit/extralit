import { defineNuxtPlugin } from "#app";
import { loadDependencyContainer } from "~/v1/di";
import { loadV2DependencyContainer } from "~/v2/di";

// Registers the ts-injecty container. Ordered last (3.) so $auth (1.) and $axios (2.)
// are available when repositories resolve. v2 loads after v1 into the same container.
export default defineNuxtPlugin((nuxtApp) => {
  loadDependencyContainer(nuxtApp as never);
  loadV2DependencyContainer(nuxtApp as never);
});
