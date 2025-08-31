import { Context } from "@nuxt/types";
import { useNotifications } from "../services";

export const loadErrorHandler = (context: Context) => {
  const axios = context.$axios;
  const t = (key: string) => context.app.i18n.t(key).toString();

  const notification = useNotifications();

  axios.onError((error) => {
    const { status, data } = error.response ?? {};

    notification.clear();

    // Prioritize specific error messages over generic HTTP status messages
    // 1. Business logic errors (highest priority)
    if (data.code) {
      const errorHandledKey = `validations.businessLogic.${data.code}.message`;
      const handledTranslatedError = t(errorHandledKey);

      if (handledTranslatedError !== errorHandledKey) {
        console.log("handledTranslatedError", errorHandledKey);
        notification.notify({
          message: handledTranslatedError,
          type: "danger",
        });
        throw error;
      }
    }

    // 2. Detailed error messages (medium priority)
    if (data.detail && typeof data.detail === "string") {
      notification.notify({
        message: data.detail.toString(),
        type: "danger",
      });
      throw error;
    }

    // 3. Generic HTTP status messages (fallback)
    const errorHandledKey = `validations.http.${status}.message`;
    const handledTranslatedError = t(errorHandledKey);

    if (handledTranslatedError !== errorHandledKey) {
      notification.notify({
        message: handledTranslatedError,
        type: "danger",
      });
    }

    throw error;
  });
};
