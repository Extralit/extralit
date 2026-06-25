import type { AxiosInstance } from "axios";
import { useNotifications } from "../services";

// Ported from the @nuxtjs/auth-next `$axios.onError` handler to a standard axios
// response interceptor. Message priority is preserved verbatim:
//   1. business-logic error (data.code) 2. detail string 3. generic HTTP status.
export const loadErrorHandler = (axios: AxiosInstance, t: (key: string) => string) => {
  const notification = useNotifications();

  axios.interceptors.response.use(
    (response) => response,
    (error) => {
      const { status, data } = error.response ?? {};

      notification.clear();

      // 1. Business logic errors (highest priority)
      if (data?.code) {
        const errorHandledKey = `validations.businessLogic.${data.code}.message`;
        const handledTranslatedError = t(errorHandledKey);

        if (handledTranslatedError !== errorHandledKey) {
          notification.notify({ message: handledTranslatedError, type: "danger" });
          return Promise.reject(error);
        }
      }

      // 2. Detailed error messages (medium priority)
      if (data?.detail && typeof data.detail === "string") {
        notification.notify({ message: data.detail.toString(), type: "danger" });
        return Promise.reject(error);
      }

      // 3. Generic HTTP status messages (fallback)
      const errorHandledKey = `validations.http.${status}.message`;
      const handledTranslatedError = t(errorHandledKey);

      if (handledTranslatedError !== errorHandledKey) {
        notification.notify({ message: handledTranslatedError, type: "danger" });
      }

      return Promise.reject(error);
    }
  );
};
