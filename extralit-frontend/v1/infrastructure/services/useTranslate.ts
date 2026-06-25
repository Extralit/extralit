export const useTranslate = () => {
  const { $i18n } = useNuxtApp();

  const t = (key: string, values?: any) => {
    return $i18n.t(key, values) as string;
  };

  const tc = (key: string, choice: number) => {
    return $i18n.t(key, choice) as string;
  };

  return { t, tc };
};
