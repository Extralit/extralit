<!--
  - coding=utf-8
  - Copyright 2021-present, the Recognai S.L. team.
  -
  - Licensed under the Apache License, Version 2.0 (the "License");
  - you may not use this file except in compliance with the License.
  - You may obtain a copy of the License at
  -
  -     http://www.apache.org/licenses/LICENSE-2.0
  -
  - Unless required by applicable law or agreed to in writing, software
  - distributed under the License is distributed on an "AS IS" BASIS,
  - WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  - See the License for the specific language governing permissions and
  - limitations under the License.
  -->

<template>
  <div class="recent-imports">
    <div class="recent-imports__header">
      <h3 class="recent-imports__title">Recent Imports</h3>
      <p class="recent-imports__subtitle">Configure datasets from your recent imports</p>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="recent-imports__loading">
      <BaseSpinner />
      <p>Loading recent imports...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="recent-imports__error">
      <BaseIcon icon-name="danger" class="recent-imports__error-icon" />
      <h4>Failed to Load Recent Imports</h4>
      <p>{{ error }}</p>
      <BaseButton variant="outline" @click="loadRecentImports"> Retry </BaseButton>
    </div>

    <!-- No Workspace Selected -->
    <div v-else-if="!hasWorkspace" class="recent-imports__no-workspace">
      <h4>Select a Workspace</h4>
      <p>Please select a workspace to view recent imports.</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="!recentImports || !recentImports.length" class="recent-imports__empty">
      <h4>No Recent Imports Found</h4>
      <p>You haven't imported any documents yet. Start by importing your first bibliography file.</p>
    </div>

    <!-- Recent Imports List -->
    <div v-else class="recent-imports__list">
      <RecentImportCard
        v-for="importRecord in recentImports || []"
        :key="importRecord.id"
        :import-record="importRecord"
        @click="$emit('import-selected', importRecord)"
      />
    </div>

    <!-- Action Buttons -->
    <div class="recent-imports__actions">
      <BaseButton variant="outline" class="recent-imports__view-all-btn" @click="$emit('view-all-imports')">
        View All Imports
      </BaseButton>
    </div>
  </div>
</template>

<script lang="ts">
import "assets/icons/danger";
import "assets/icons/document";
import "assets/icons/import";
import { useRecentImportsViewModel } from "./useRecentImportsViewModel";
import { Workspace } from "~/v1/domain/entities/workspace/Workspace";

export default {
  name: "RecentImports",

  props: {
    workspace: {
      type: Workspace,
      default: null,
    },
  },

  emits: ["import-selected", "view-all-imports", "import-documents"],

  setup(props) {
    return useRecentImportsViewModel(props);
  },
};
</script>

<style lang="scss" scoped>
.recent-imports {
  display: flex;
  flex-direction: column;
  gap: $base-space * 2;

  &__header {
    .recent-imports__title {
      margin: 0 0 $base-space 0;
      font-weight: 500;
      color: var(--fg-primary);
      @include font-size(16px);
    }

    .recent-imports__subtitle {
      margin: 0;
      color: var(--fg-secondary);
      @include font-size(14px);
      font-weight: 300;
      @include line-height(18px);
    }
  }

  // Loading state
  &__loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: $base-space * 4;
    gap: $base-space * 2;

    p {
      margin: 0;
      color: var(--fg-secondary);
      @include font-size(14px);
    }
  }

  // Error state
  &__error {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: $base-space * 4;
    gap: $base-space * 2;
    text-align: center;

    &-icon {
      @include font-size(32px);
      color: var(--color-danger);
    }

    h4 {
      margin: 0;
      color: var(--color-danger);
      @include font-size(16px);
      font-weight: 600;
    }

    p {
      margin: 0;
      color: var(--fg-primary);
      @include font-size(14px);
      max-width: 300px;
      @include line-height(20px);
    }
  }

  // No workspace state
  &__no-workspace {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: $base-space * 4;
    gap: $base-space * 2;
    text-align: center;

    .recent-imports__empty-icon {
      @include font-size(32px);
      color: var(--fg-secondary);
    }

    h4 {
      margin: 0;
      color: var(--fg-primary);
      @include font-size(16px);
      font-weight: 600;
    }

    p {
      margin: 0;
      color: var(--fg-secondary);
      @include font-size(14px);
      max-width: 300px;
      @include line-height(20px);
    }
  }

  // Empty state
  &__empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: $base-space * 4;
    gap: $base-space * 2;
    text-align: center;

    &-icon {
      @include font-size(32px);
      color: var(--fg-secondary);
    }

    h4 {
      margin: 0;
      color: var(--fg-primary);
      @include font-size(16px);
      font-weight: 600;
    }

    p {
      margin: 0;
      color: var(--fg-secondary);
      @include font-size(14px);
      max-width: 300px;
      @include line-height(20px);
    }
  }

  // Recent imports list
  &__list {
    display: flex;
    flex-direction: column;
    gap: $base-space * 2;
  }

  // Action buttons
  &__actions {
    display: flex;
    flex-direction: column;
    gap: $base-space;
    margin-top: $base-space;

    .recent-imports__view-all-btn {
      @include font-size(14px);
    }

    .recent-imports__import-btn {
      display: flex;
      align-items: center;
      gap: calc($base-space / 2);
      @include font-size(14px);

      .recent-imports__import-icon {
        flex-shrink: 0;
        width: 16px;
        height: 16px;
      }
    }
  }
}

// Responsive design
@include media("<tablet") {
  .recent-imports {
    &__header {
      .recent-imports__title {
        @include font-size(15px);
      }

      .recent-imports__subtitle {
        @include font-size(13px);
      }
    }

    &__actions {
      .recent-imports__view-all-btn,
      .recent-imports__import-btn {
        @include font-size(13px);
      }
    }
  }
}
</style>
