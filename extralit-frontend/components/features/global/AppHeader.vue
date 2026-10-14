<template>
  <section id="header" ref="header" class="header">
    <BaseTopbarBrand>
      <BaseBreadcrumbs
        role="button"
        aria-label="Home button"
        :breadcrumbs="breadcrumbs"
        @breadcrumb-action="onBreadcrumbAction"
      />

      <UserAvatarTooltip />
    </BaseTopbarBrand>
  </section>
</template>

<script lang="ts">
import { type BreadcrumbItem } from "~/v1/infrastructure/types/breadcrumb";

export default {
  data() {
    return {
      headerHeight: null,
    };
  },
  props: {
    breadcrumbs: {
      type: Array as () => BreadcrumbItem[],
    },
  },
  methods: {
    onBreadcrumbAction(action) {
      this.$emit("breadcrumb-action", action);
    },
  },
};
</script>

<style lang="scss" scoped>
$header-button-color: #262a2e;
.header {
  opacity: 1;
  transition: none;
  top: 0;
  right: 0;
  left: 0;
  transform: translateY(0);
  position: sticky;
  z-index: 3;
  :deep(.header__filters) {
    position: relative;
  }
  &:not(.sticky) {
    position: relative;
  }
}

.button-settings {
  margin-right: $base-space;
  &[data-title] {
    position: relative;
    overflow: visible;
    @extend %has-tooltip--bottom;
    &:before,
    &:after {
      margin-top: calc($base-space/2);
    }
  }
}
.header__button {
  background: $header-button-color;
  color: var(--color-white);
  margin-right: $base-space;
  padding: 10px 12px 10px 10px;
  font-weight: 600;
  @include font-size(14px);
  box-shadow: $shadow-200;
  &:hover {
    background: lighten($header-button-color, 3%);
  }
  svg {
    fill: var(--color-white);
  }
}
</style>
