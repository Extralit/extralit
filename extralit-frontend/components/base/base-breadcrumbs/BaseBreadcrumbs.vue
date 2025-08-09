<template>
  <div class="breadcrumbs">
    <ul role="navigation">
      <li v-for="(breadcrumb, index) in filteredBreadcrumbs" :key="breadcrumb.name">
        <!-- Render workspace breadcrumb dropdown for workspace items -->
        <WorkspaceBreadcrumbDropdown
          v-if="breadcrumb.isWorkspace"
          :workspace-id="breadcrumb.workspaceId"
          :is-last-breadcrumb="index === filteredBreadcrumbs.length - 1"
          @workspace-change="onWorkspaceChange(breadcrumb, $event)"
        />
        <!-- Render normal breadcrumb items -->
        <nuxt-link
          v-else-if="breadcrumb.link"
          class="breadcrumbs__item"
          :to="breadcrumb.link"
        >
          {{ breadcrumb.name }}
        </nuxt-link>
        <span
          v-else
          class="breadcrumbs__item --action"
          @click="onBreadcrumbAction(breadcrumb)"
        >
          {{ breadcrumb.name }}
        </span>
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

<script lang="ts">
import { BreadcrumbItem, WorkspaceChangeEvent } from "~/v1/infrastructure/types/breadcrumb";
import WorkspaceBreadcrumbDropdown from "./WorkspaceBreadcrumbDropdown.vue";

export default {
  components: {
    WorkspaceBreadcrumbDropdown,
  },
  props: {
    breadcrumbs: {
      type: Array as () => BreadcrumbItem[],
      default: () => [],
    },
    copyButton: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    filteredBreadcrumbs(): BreadcrumbItem[] {
      return this.breadcrumbs.filter((breadcrumb) => breadcrumb.name);
    },
  },
  methods: {
    onBreadcrumbAction(breadcrumb: BreadcrumbItem) {
      this.$emit("breadcrumb-action", breadcrumb.action);
    },
    onWorkspaceChange(breadcrumb: BreadcrumbItem, event: WorkspaceChangeEvent) {
      // Update the breadcrumb link with the new workspace information
      const updatedBreadcrumb = {
        ...breadcrumb,
        link: event.link,
        workspaceId: event.workspaceId,
      };

      // Emit breadcrumb link update event
      this.$emit("breadcrumb-link-update", {
        breadcrumb: updatedBreadcrumb,
        workspaceChange: event,
      });

      // Also emit the workspace change event for parent components
      this.$emit("workspace-change", event);
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
