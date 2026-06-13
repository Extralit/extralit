import { useLocalStorage } from "./useLocalStorage";

type Locale = { code: string };

type Context = {
  app: {
    i18n: {
      locales: Locale[];
      setLocale: (locale: string) => void | Promise<void>;
    };
  };
};

export const useLanguageDetector = (context: Context) => {
  const { change } = useLanguageChanger(context);
  const { get } = useLocalStorage();

  const { i18n } = context.app;

  const detect = () => {
    return get<string>("language") || navigator.language;
  };

  const exists = (language: string) => {
    return i18n.locales.some((l) => l.code === language);
  };

  const initialize = () => {
    const language = detect();

    if (exists(language)) {
      return change(language);
    }

    const languageCode = language.split("-")[0];

    if (exists(languageCode)) {
      return change(languageCode);
    }

    change("en");
  };

  return {
    initialize,
  };
};

export const useLanguageChanger = (context: Context) => {
  const { i18n } = context.app;

  const { set } = useLocalStorage();

  const change = (language: string) => {
    i18n.setLocale(language);
    document.documentElement.lang = language;

    set("language", language);
  };

  return {
    change,
    languages: i18n.locales.sort((a, b) => a.code.localeCompare(b.code)),
  };
};
