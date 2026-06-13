import { useLanguageChanger } from "~/v1/infrastructure/services";

export const useUserSettingsLanguageViewModel = () => {
  const context = { app: { i18n: useNuxtApp().$i18n } };
  const { change, languages } = useLanguageChanger(context);

  return {
    change,
    languages,
  };
};
