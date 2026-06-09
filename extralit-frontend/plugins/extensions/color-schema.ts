import { Inject } from "@nuxt/types/app";
import { useColorSchema } from "~/v1/infrastructure/services/useColorSchema";

export default (_, inject: Inject) => {
  const colorSchema = useColorSchema();

  colorSchema.initialize();

  inject("colorSchema", colorSchema);
};
