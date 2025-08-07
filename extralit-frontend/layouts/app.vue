<template>
  <div :lang="currentLang">
    <Nuxt v-if="!$slots.default" />
    <slot />
  </div>
</template>

<script>
export default {
  name: "Index",
  computed: {
    imOffline() {
      return this.$nuxt.isOffline;
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
