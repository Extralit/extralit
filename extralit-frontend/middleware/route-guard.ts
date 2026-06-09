import { Context } from "@nuxt/types";
import { useRunningEnvironment } from "~/v1/infrastructure/services/useRunningEnvironment";
import { useLocalStorage } from "~/v1/infrastructure/services";

const { set } = useLocalStorage();

export default ({ $auth, route, redirect }: Context) => {
  const { isRunningOnHuggingFace } = useRunningEnvironment();

  // By-pass unknown routes. This is needed to avoid errors with API calls.
  if (route.name == null) return;

  switch (route.name) {
    case "sign-in":
      if ($auth.loggedIn) return redirect("/");

      if (route.params.omitCTA) return;

      if (isRunningOnHuggingFace()) {
        return redirect({
          name: "welcome-hf-sign-in",
        });
      }
      break;
    case "oauth-provider-callback":
      if (!Object.keys(route.query).length) return redirect("/");

      break;
    case "welcome-hf-sign-in":
      if ($auth.loggedIn) return redirect("/");

      if (!isRunningOnHuggingFace()) return redirect("/");

      break;
    default:
      if (!$auth.loggedIn) {
        if (route.path !== "/") {
          set("redirectTo", route.fullPath);
        }

        redirect({
          name: "sign-in",
        });
      }
  }
};
