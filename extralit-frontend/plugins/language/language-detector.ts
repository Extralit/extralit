import { Context } from "@nuxt/types";
import { useLanguageDetector } from "~/v1/infrastructure/services/useLanguageDetector";

export default (context: Context) => {
  const { initialize } = useLanguageDetector(context);

  initialize();
};
