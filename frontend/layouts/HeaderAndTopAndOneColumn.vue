<template>
  <div class="layout" :class="layoutClass">
    <div class="header-area">
      <slot name="header">here is the header</slot>
    </div>
    <div class="sidebar-area">
      <slot name="sidebar-right">here is the sidebar content right</slot>
    </div>
    <div class="center-area">
      <slot name="center">here is the center content</slot>
    </div>
  </div>
</template>

<script>
export default {
  name: "HeaderAndTopAndOneColumnsLayout",
  data: () => {
    return {
      sidebarPanel: null,
    };
  },
  computed: {
    layoutClass() {
      return this.sidebarPanel ? "--panel" : null;
    },
  },
  created() {
    this.$nuxt.$on("on-sidebar-panel", (value) => {
      this.sidebarPanel = value;
    });
  },
  afterDestroy() {
    this.$nuxt.$off("on-sidebar-panel");
  },
};
</script>

<style lang="scss" scoped>
$gap-width: $base-space * 2;
.layout {
  display: grid;
  grid-template-columns: 1fr $sidebarMenuWidth;
  grid-template-rows: auto minmax(0, 1fr) auto;
  grid-column-gap: 0px;
  grid-row-gap: 0px;
  grid-template-areas:
    "header header"
    "center sidebar";
  height: 100vh;
  transition: 0.4s ease-in-out;
  @include media("<desktop") {
    height: 100svh;
    grid-template-areas:
      "header header"
      "center center";
  }
  &.--panel {
    @include media(">desktop") {
      grid-template-columns: 1fr var(--sidebar-width);
      transition: none;
    }
  }
}

.header-area {
  grid-area: header;
}
.sidebar-area {
  grid-area: sidebar;
}
.center-area {
  grid-area: center;
  min-width: 0;
  @include media("<desktop") {
    min-height: 0;
  }
}
</style>
