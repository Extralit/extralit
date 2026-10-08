<template>
  <div :lang="currentLang">
    <slot />
  </div>
</template>

<script>
import { useOnline } from "@vueuse/core";

export default {
  name: "Index",
  setup() {
    return { online: useOnline() };
  },
  computed: {
    imOffline() {
      return !this.online;
    },
    currentLang() {
      return this.$i18n.locale;
    },
  },
  watch: {
    imOffline(isOffline, wasOffline) {
      if (isOffline) {
        return this.showNotification(this.$t("youAreOffline"));
      }

      if (wasOffline) {
        return this.showNotification(this.$t("youAreOnlineAgain"));
      }
    },
  },
  methods: {
    showNotification(message) {
      this.$notification.notify({
        message: message,
        type: "danger",
      });
    },
  },
};
</script>
