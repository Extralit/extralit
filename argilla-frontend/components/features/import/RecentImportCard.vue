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
  <BaseButton class="import-card" @click="$emit('click')">
    <div class="import-card__content">
      <div class="import-card__header">
        <h4 class="import-card__filename">{{ importRecord.filename }}</h4>
        <span class="import-card__date">
          <BaseIcon icon-name="time" class="import-card__date-icon" />
          {{ formatDate(importRecord.created_at) }}
        </span>
      </div>
      <div class="import-card__stats">
        <div class="import-card__stat">
          <span class="import-card__stat-count">{{ importRecord.total_papers }}</span>
          <span class="import-card__stat-label">papers</span>
        </div>
        <div class="import-card__stat import-card__stat--success">
          <span class="import-card__stat-count">{{ importRecord.success_count }}</span>
          <span class="import-card__stat-label">success</span>
        </div>
        <div
          v-if="importRecord.failed_count > 0"
          class="import-card__stat import-card__stat--failed"
        >
          <span class="import-card__stat-count">{{ importRecord.failed_count }}</span>
          <span class="import-card__stat-label">failed</span>
        </div>
      </div>
    </div>
  </BaseButton>
</template>

<script lang="ts">
import "assets/icons/time";
import type { ImportHistoryListItem } from "~/v1/domain/usecases/get-import-history-use-case";

export default {
  name: "RecentImportCard",

  props: {
    importRecord: {
      type: Object as () => ImportHistoryListItem,
      required: true,
    },
  },

  emits: ["click"],

  methods: {
    formatDate(dateString: string): string {
      const date = new Date(dateString);
      const now = new Date();
      const diffTime = Math.abs(now.getTime() - date.getTime());
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

      if (diffDays === 1) {
        return "Yesterday";
      } else if (diffDays < 7) {
        return `${diffDays} days ago`;
      } else {
        return date.toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        });
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.import-card {
  &.button {
    width: 100%;
    max-width: 75%;
    padding: $base-space * 2;
    border: 1px solid var(--bg-opacity-6);
    border-radius: $border-radius-m;
    background: var(--bg-accent-grey-2);
    color: var(--fg-primary);
    text-align: left;

    @include media("<desktop") {
      max-width: 100%;
    }

    &:hover {
      border-color: var(--bg-opacity-10);
      background: var(--bg-accent-grey-3);
    }
  }

  &__content {
    display: flex;
    flex-direction: column;
    gap: $base-space * 2;
  }

  &__header {
    display: flex;
    flex-direction: column;
    gap: calc($base-space / 2);
  }

  &__filename {
    margin: 0;
    color: var(--fg-primary);
    font-weight: 500;
    font-size: 0.95rem;
    @include line-height(18px);

    // Truncate long filenames
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__date {
    display: flex;
    align-items: center;
    gap: calc($base-space / 2);
    color: var(--fg-tertiary);
    @include font-size(12px);

    &-icon {
      flex-shrink: 0;
      width: 12px;
      height: 12px;
    }
  }

  &__stats {
    display: flex;
    gap: $base-space;
    flex-wrap: wrap;
  }

  &__stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: calc($base-space / 4);

    &-count {
      font-weight: 600;
      font-size: 0.9rem;
      color: var(--fg-primary);
    }

    &-label {
      font-size: 0.75rem;
      color: var(--fg-secondary);
      text-transform: lowercase;
    }

    &--success {
      .import-card__stat-count {
        color: var(--color-success);
      }
    }

    &--failed {
      .import-card__stat-count {
        color: var(--color-danger);
      }
    }
  }
}

// Responsive design
@media (max-width: 768px) {
  .import-card {
    &__filename {
      font-size: 0.9rem;
    }

    &__stats {
      gap: calc($base-space / 2);
    }

    &__stat {
      &-count {
        font-size: 0.85rem;
      }

      &-label {
        font-size: 0.7rem;
      }
    }
  }
}
</style>