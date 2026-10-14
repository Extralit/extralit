<template>
  <main class="internal-page">
    <div class="internal-page__header">
      <slot name="header" />
    </div>
    <main class="internal-page__container">
      <!-- No placeholder fallbacks: an unfilled slot must render nothing. The inherited
      "here is the page header" / "here is the page content" defaults were dev scaffolding
      and rendered as literal copy on every page that fills only some of these slots
      (e.g. /extractions, which supplies `header` + `page-content` but no `page-header`). -->
      <slot name="page-header" />
      <slot name="page-content" />
    </main>
  </main>
</template>

<script>
export default {
  name: "InternalPage",
};
</script>

<style lang="scss" scoped>
.internal-page {
  background: var(--bg-accent-grey-1);
  &__container {
    display: flex;
    flex-direction: column;
    height: calc(100vh - $topbarHeight);
    overflow: auto;
    max-width: 1500px;
    padding: 0 $base-space * 8;
    margin: 0 auto;
    @include media("<desktop") {
      padding: 0 $base-space * 2;
    }
  }
}
</style>
