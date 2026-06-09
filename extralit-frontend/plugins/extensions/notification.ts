import { Inject } from "@nuxt/types/app";
import { useNotifications } from "~/v1/infrastructure/services/useNotifications";

export default (_, inject: Inject) => {
  const notification = useNotifications();

  inject("notification", notification);
};
