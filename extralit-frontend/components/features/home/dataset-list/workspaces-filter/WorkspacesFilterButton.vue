<template>
  <FilterButton :button-name="buttonDisplayName" icon-name="filter" :is-button-active="isButtonActive" />
</template>

<script>
export default {
  props: {
    isActive: {
      type: Boolean,
      default: false,
    },
    selectedWorkspace: {
      type: String,
      default: null,
    },
  },
  computed: {
    isButtonActive() {
      return this.isActive;
    },
    buttonDisplayName() {
      return this.selectedWorkspace || this.$t("Workspaces");
    },
  },
};
</script>

<style lang="scss" scoped>
.filter-button--active {
  background: var(--bg-opacity-4);
  &:hover {
    background: var(--bg-opacity-6);
  }
}
</style>
