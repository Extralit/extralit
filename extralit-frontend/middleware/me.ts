import { Context } from "@nuxt/types";
import { useResolve } from "ts-injecty";
import { LoadUserUseCase } from "~/v1/domain/usecases/load-user-use-case";

export default async ({ $auth }: Context) => {
  const useCase = useResolve(LoadUserUseCase);

  try {
    await useCase.execute();
  } catch (e) {
    if (e.response.status === 401) {
      await $auth.logout();

      $auth.redirect("login");
    }
  }
};
