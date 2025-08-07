<template>
  <div class="breadcrumbs">
    <ul role="navigation">
      <li v-for="breadcrumb in filteredBreadcrumbs" :key="breadcrumb.name">
        <nuxt-link v-if="breadcrumb.link" class="breadcrumbs__item" :to="breadcrumb.link"
          >{{ breadcrumb.name }}
        </nuxt-link>
        <span v-else class="breadcrumbs__item --action" @click="onBreadcrumbAction(breadcrumb)">{{
          breadcrumb.name
        }}</span>
      </li>
    </ul>
    <!-- <base-action-tooltip :tooltip="$t('copied')">
      <a
        v-if="copyButton"
        class="breadcrumbs__copy"
        @click.prevent="
          $copyToClipboard(
            filteredBreadcrumbs.slice(-2).map(breadcrumb => breadcrumb.name).join('/')
          )
        "
      >
        <svgicon name="copy" width="16" height="16" />
      </a>
    </base-action-tooltip> -->
  </div>
</template>

<script>
export default {
  props: {
    breadcrumbs: {
      type: Array,
      default: () => [],
    },
    copyButton: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    filteredBreadcrumbs() {
      return this.breadcrumbs.filter((breadcrumb) => breadcrumb.name);
    },
  },
  methods: {
    onBreadcrumbAction(breadcrumb) {
      this.$emit("breadcrumb-action", breadcrumb.action);
    },
  },
};
</script>

<style lang="scss" scoped>
.breadcrumbs {
  margin-left: 1em;
  display: flex;
  align-items: center;
  ul {
    display: flex;
    padding-left: 0;
    font-weight: normal;
    list-style: none;
    @include media("<=tablet") {
      flex-wrap: wrap;
    }
  }
  li {
    margin: auto 0.5em auto auto;
    white-space: nowrap;
    @include media("<=tablet") {
      margin: 0;
    }
    &:not(:last-child):after {
      content: "/";
      margin-left: 0.5em;
    }
    &:last-child {
      word-break: break-all;
      white-space: pre-line;
      font-weight: 600;
      a {
        cursor: default;
        pointer-events: none;
      }
    }
  }
  &__item {
    color: var(--fg-lighter);
    text-decoration: none;
    outline: none;
    &.--action {
      cursor: pointer;
    }
  }
}
</style>
