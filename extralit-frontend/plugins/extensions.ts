import { unref } from "vue";
import { defineNuxtPlugin, useRuntimeConfig } from "#app";
import Draggable from "vuedraggable";
import { Color } from "~/v1/domain/entities/color/Color";
import { useColorSchema } from "~/v1/infrastructure/services/useColorSchema";
import { useClipboard } from "~/v1/infrastructure/services/useClipboard";
import { useNotifications } from "~/v1/infrastructure/services/useNotifications";
import { usePlatform } from "~/v1/infrastructure/services/usePlatform";
import { useLanguageDirection } from "~/v1/infrastructure/services/useLanguageDirection";
import { useLanguageDetector } from "~/v1/infrastructure/services/useLanguageDetector";

// Consolidates the former plugins/extensions/*, plugins/language/* and plugins/logo/*.
// inject("x", v) -> provide:{ x: v } (exposed as $x on the Nuxt app + components).
export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.vueApp.component("draggable", Draggable);

  const colorSchema = useColorSchema();
  colorSchema.initialize();

  const { copy } = useClipboard();
  const notification = useNotifications();
  const platform = usePlatform();
  const language = useLanguageDirection();

  // Language detection needs the i18n locales list + setLocale.
  const i18n = (nuxtApp as { $i18n?: { locales: unknown; setLocale: unknown } }).$i18n;
  if (i18n) {
    const { initialize } = useLanguageDetector({
      app: { i18n: { locales: unref(i18n.locales), setLocale: i18n.setLocale } },
    } as never);
    initialize();
  }

  const config = useRuntimeConfig();
  // eslint-disable-next-line no-console
  console.log(`%c${new Date().getFullYear()} Extralit (${config.public.clientVersion})`, "color:#F88989");

  return {
    provide: {
      color: Color,
      colorSchema,
      copyToClipboard: copy,
      notification,
      platform,
      language,
    },
  };
});
