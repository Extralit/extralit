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
  <BaseButton class="recent-import-card" @click="$emit('click')">
    <div class="recent-import-card__content">
      <div class="recent-import-card__header">
        <h4 class="recent-import-card__filename">{{ importRecord.filename }}</h4>
        <span class="recent-import-card__date">
          <BaseIcon icon-name="time" class="recent-import-card__date-icon" />
          {{ formatDate(importRecord.created_at) }}
        </span>
      </div>
      <div class="recent-import-card__stats">
        <div class="recent-import-card__stat">
          <span class="recent-import-card__stat-count">{{ totalPapers }}</span>
          <span class="recent-import-card__stat-label">papers</span>
        </div>
        <div class="recent-import-card__stat recent-import-card__stat--success">
          <span class="recent-import-card__stat-count">{{ importRecord.success_count }}</span>
          <span class="recent-import-card__stat-label">success</span>
        </div>
        <div v-if="importRecord.failed_count > 0" class="recent-import-card__stat recent-import-card__stat--failed">
          <span class="recent-import-card__stat-count">{{ importRecord.failed_count }}</span>
          <span class="recent-import-card__stat-label">failed</span>
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

  computed: {
    totalPapers(): number {
      return this.importRecord.total_papers || 0;
    },
  },

  methods: {
    formatDate(dateString: string): string {
      try {
        const date = new Date(dateString);
        const now = Date.now();
        const diffInMs = now - date.getTime();
        const diffInHours = Math.floor(diffInMs / (1000 * 60 * 60));
        const diffInDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24));

        // Check if date is invalid
        if (isNaN(date.getTime())) {
          return "Unknown";
        }

        if (diffInMs < 0) {
          // Future date
          return date.toLocaleDateString();
        } else if (diffInMs < 60 * 60 * 1000) {
          // Less than 1 hour
          return "Just now";
        } else if (diffInHours < 24) {
          // Less than 24 hours
          return `${diffInHours}h ago`;
        } else if (diffInDays === 1) {
          // Exactly 1 day ago
          return "Yesterday";
        } else if (diffInDays < 7) {
          // Less than 7 days
          return `${diffInDays}d ago`;
        } else {
          // More than 7 days
          return date.toLocaleDateString();
        }
      } catch (error) {
        console.error("Error formatting date:", error);
        return "Unknown";
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.recent-import-card {
  &.button {
    width: 100%;
    max-width: 75%;
    padding: $base-space * 2;
    border: 1px solid var(--bg-opacity-6);
    border-radius: $border-radius-m;
    background: var(--bg-accent-grey-2);
    color: var(--fg-primary);
    text-align: left;
    transition: all 0.2s ease;

    @include media("<desktop") {
      max-width: 100%;
    }

    &:hover {
      border-color: var(--bg-opacity-10);
      background: var(--bg-accent-grey-3);
      transform: translateY(-1px);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }

    &:active {
      transform: translateY(0);
      box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
    }

    &:focus {
      outline: 2px solid var(--bg-action);
      outline-offset: 2px;
    }

    &:focus:not(:focus-visible) {
      outline: none;
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
    @include font-size(15px);
    font-weight: 500;
    @include line-height(18px);
    word-break: break-word;
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  &__date {
    display: flex;
    align-items: center;
    gap: calc($base-space / 2);
    margin: 0;
    color: var(--fg-tertiary);
    @include font-size(12px);

    &-icon {
      flex-shrink: 0;
      width: 12px;
      height: 12px;
      opacity: 0.7;
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
    min-width: 0;

    &-count {
      @include font-size(14px);
      font-weight: 600;
      color: var(--fg-primary);
    }

    &-label {
      @include font-size(10px);
      font-weight: 400;
      color: var(--fg-secondary);
      text-transform: lowercase;
    }

    &--success {
      .recent-import-card__stat-count {
        color: var(--color-success);
      }
    }

    &--failed {
      .recent-import-card__stat-count {
        color: var(--color-danger);
      }
    }
  }
}

// Responsive design
@include media("<tablet") {
  .recent-import-card {
    &.button {
      padding: $base-space * 1.5;
    }

    &__filename {
      @include font-size(14px);
    }

    &__date {
      @include font-size(11px);
    }

    &__stat {
      &-count {
        @include font-size(13px);
      }

      &-label {
        @include font-size(9px);
      }
    }
  }
}

@include media("<phone") {
  .recent-import-card {
    &.button {
      padding: $base-space * 1.25;
    }

    &__filename {
      @include font-size(13px);
      @include line-height(16px);
    }

    &__date {
      @include font-size(10px);
    }

    &__stats {
      gap: calc($base-space / 2);
    }

    &__stat {
      &-count {
        @include font-size(12px);
      }

      &-label {
        @include font-size(8px);
      }
    }
  }
}
</style>