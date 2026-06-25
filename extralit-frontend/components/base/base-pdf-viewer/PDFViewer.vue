<template>
  <div class="pdf-container">
    <!--
      NOTE (Vue 3 migration): the previous renderer, @jonnytran/vue-pdf-viewer@0.2.5,
      is Vue-2-only (its bundle and its deps vue-dropzone / vue-in-viewport call the
      Vue 2 global API at module scope) and cannot run under Vue 3. It has been
      replaced with this placeholder. Follow-up: publish a Vue-3 build of
      @jonnytran/vue-pdf-viewer (or swap to a Vue-3 renderer such as vue-pdf-embed)
      and restore the full toolbar/sidebar/scale/page-navigation UI here.
    -->
    <div class="pdf-placeholder">
      <p class="pdf-placeholder__title">{{ fileName }}</p>
      <p class="pdf-placeholder__message">{{ $t("document.viewerUnavailable") }}</p>
      <a v-if="url" :href="url" target="_blank" rel="noopener" class="pdf-placeholder__link">
        {{ $t("document.openInNewTab") }}
      </a>
    </div>
  </div>
</template>

<script lang="ts">
export default {
  name: "PDFViewer",

  props: {
    url: {
      type: String,
      required: true,
    },
    fileName: {
      type: String,
      required: false,
    },
    pageNumber: {
      type: [Number, String],
      required: false,
    },
  },
};
</script>

<style scoped lang="scss">
.pdf-container {
  position: relative;
  font-family: "Avenir", Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  height: 100%;
}

.pdf-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: $base-space;
  height: 100%;
  padding: $base-space * 2;

  &__title {
    font-size: 14px;
    font-weight: 600;
    margin: 0;
  }

  &__message {
    color: var(--color-dark-grey);
    margin: 0;
  }

  &__link {
    color: var(--color-primary);
    text-decoration: underline;
  }
}
</style>
