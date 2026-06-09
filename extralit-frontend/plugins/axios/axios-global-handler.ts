import { Context } from "@nuxt/types";
import { loadErrorHandler } from "~/v1/infrastructure/repositories/AxiosErrorHandler";

export default (context: Context) => {
  loadErrorHandler(context);
};
