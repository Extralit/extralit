declare global {
  interface Navigator {
    userLanguage?: string;
    systemLanguage?: string;
  }
}

const getLocales = (): string[] => {
  if (typeof navigator === "undefined") return [];
  return [...(navigator.languages || []), navigator.language, navigator.userLanguage, navigator.systemLanguage].filter(
    Boolean
  ) as string[];
};

/** Locale-grouped integer formatting (replaces the `formatNumber` Vue filter). */
export const formatNumber = (value: number): string => {
  const locales = getLocales();
  return new Intl.NumberFormat(locales.length ? locales[0] : "en").format(value);
};

/** Compact K/M notation (replaces the `formatNumberToK` Vue filter). */
export const formatNumberToK = (value: number, maximumFractionDigits: number): string =>
  value.toLocaleString("en-US", {
    maximumFractionDigits,
    notation: "compact",
    compactDisplay: "short",
  });
