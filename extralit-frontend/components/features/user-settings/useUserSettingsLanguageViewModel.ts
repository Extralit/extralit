import { useLanguageChanger } from "~/v1/infrastructure/services";

export const useUserSettingsLanguageViewModel = () => {
  // $i18n is the Nuxt i18n Composer; at runtime it carries the locales/setLocale
  // members useLanguageChanger needs, but its static type (vue-i18n Composer)
  // shapes `locales` differently, so we cast through the expected context shape.
  const context = { app: { i18n: useNuxtApp().$i18n } } as unknown as Parameters<
    typeof useLanguageChanger
  >[0];
  const { change, languages } = useLanguageChanger(context);

  return {
    change,
    languages,
  };
};
