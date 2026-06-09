import { Context } from "@nuxt/types";
import { loadDependencyContainer } from "@/v1/di";

export default (context: Context) => {
  loadDependencyContainer(context);
};
