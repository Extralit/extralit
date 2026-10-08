import { useRunningEnvironment } from "~/v1/infrastructure/services/useRunningEnvironment";
import { useLocalStorage } from "~/v1/infrastructure/services";

// Was router.middleware "route-guard" (runs first; numeric prefix preserves order).
export default defineNuxtRouteMiddleware((to) => {
  const { $auth } = useNuxtApp();
  const { set } = useLocalStorage();
  const { isRunningOnHuggingFace } = useRunningEnvironment();

  // By-pass unknown routes. This is needed to avoid errors with API calls.
  if (to.name == null) return;

  switch (to.name) {
    case "sign-in":
      if ($auth.loggedIn) return navigateTo("/");

      // Query, not params: Vue Router 4 strips non-path `params` on name-based navigation,
      // so the welcome page passes omitCTA as a query param (see welcome-hf-sign-in.vue).
      if (to.query.omitCTA) return;

      if (isRunningOnHuggingFace()) {
        return navigateTo({ name: "welcome-hf-sign-in" });
      }
      break;
    case "oauth-provider-callback":
      if (!Object.keys(to.query).length) return navigateTo("/");

      break;
    case "welcome-hf-sign-in":
      if ($auth.loggedIn) return navigateTo("/");

      if (!isRunningOnHuggingFace()) return navigateTo("/");

      break;
    default:
      if (!$auth.loggedIn) {
        if (to.path !== "/") {
          set("redirectTo", to.fullPath);
        }

        return navigateTo({ name: "sign-in" });
      }
  }
});
