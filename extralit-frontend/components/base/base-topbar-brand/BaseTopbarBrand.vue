<template>
  <div class="topbar" role="banner" aria-label="Top navigation bar">
    <brand-icon class="brand-icon" color="white" aria-label="Extralit icon" />
    <slot />
  </div>
</template>

<script>
export default {
  data: () => ({}),
};
</script>

<style lang="scss" scoped>
.topbar {
  width: 100%;
  display: flex;
  align-items: center;
  min-height: $topbarHeight;
  position: relative;
  background: var(--bg-black);
  color: var(--fg-lighter);
  padding-top: 0;
  padding-bottom: 0;
  padding-right: 1.2em;
  padding-left: $base-space * 2;
  border: 1px solid var(--bg-opacity-1);
  a {
    text-decoration: none;
    @include media("<=tablet") {
      flex-shrink: 0;
    }
  }
}
.brand-icon {
  width: 32px;
  height: auto;
}
</style>
