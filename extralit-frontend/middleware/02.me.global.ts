import { useResolve } from "ts-injecty";
import { LoadUserUseCase } from "~/v1/domain/usecases/load-user-use-case";

// Was router.middleware "me" (runs after route-guard).
export default defineNuxtRouteMiddleware(async () => {
  const { $auth } = useNuxtApp();
  const useCase = useResolve(LoadUserUseCase);

  try {
    await useCase.execute();
  } catch (e: any) {
    if (e?.response?.status === 401) {
      await $auth.logout();

      return navigateTo("/sign-in");
    }
  }
});
