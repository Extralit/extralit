<template>
  <ul class="tabs">
    <li v-for="{ id, name } in tabs" :key="id" class="tab">
      <button :id="id" :class="['tab__button', `--${tabSize}`, getTabClass(id)]" @click="changeTab(id)">
        <span>{{ name }}</span>
      </button>
    </li>
  </ul>
</template>
<script lang="ts">
export default {
  props: {
    tabs: {
      type: Array as () => { id: string; name: string }[],
      required: true,
    },
    activeTab: {
      type: Object,
      required: true,
    },
    tabSize: {
      type: String as () => "small" | "medium" | "large",
      default: "small",
    },
  },
  methods: {
    changeTab(id) {
      this.$emit("change-tab", id);
    },
    getTabClass(id) {
      return this.activeTab.id === id || this.tabs.length === 1 ? "--active" : null;
    },
  },
};
</script>
<style lang="scss" scoped>
.tabs {
  position: relative;
  display: flex;
  flex-shrink: 0;
  padding: 0;
  margin-bottom: 0;
  list-style: none;
  overflow-y: auto;
  border-bottom: 1px solid var(--bg-opacity-10);
  @extend %hide-scrollbar;
}
.tab {
  display: flex;
  &__button {
    padding: $base-space;
    background: none;
    border-top: 0;
    border-right: 0;
    border-left: 0;
    border-bottom: 2px solid transparent;
    transition: border-color 0.3s ease-in-out;
    color: var(--fg-secondary);
    outline: 0;
    white-space: nowrap;
    cursor: pointer;
    &.--small {
      @include font-size(13px);
    }
    &.--large {
      @include font-size(16px);
      padding: $base-space $base-space * 2;
    }
    &.--active {
      border-color: var(--fg-cuaternary);
      transition: border-color 0.3s ease-in-out;
    }
    &.--active,
    &:hover {
      color: var(--fg-primary);
      transition: color 0.2s ease-in-out;
    }
  }
}
</style>
