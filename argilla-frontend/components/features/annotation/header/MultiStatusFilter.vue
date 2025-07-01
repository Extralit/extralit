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
  <div v-if="options.length" class="filter-multi-status">
    <BaseDropdown :visible="dropdownIsVisible" @visibility="onVisibility">
      <span slot="dropdown-header">
        <BaseButton
          class="selected-option"
          :data-title="$t('status')"
        >
          {{ displayText }}
          <svgicon
            name="chevron-down"
            width="8"
            height="8"
            aria-hidden="true"
          />
        </BaseButton>
      </span>
      <span slot="dropdown-content">
        <div class="multi-status-options">
          <div class="multi-status-header">
            <p class="multi-status-title">{{ $t('filterByStatus') }}</p>
            <BaseButton 
              v-if="hasSelections"
              class="clear-all-btn"
              @click="clearAll"
            >
              {{ $t('clearAll') }}
            </BaseButton>
          </div>
          <ul class="options" role="group">
            <li
              v-for="{ id, name, color } in options"
              class="option"
              :class="{ selected: isSelected(id) }"
              :key="id"
              tabindex="0"
              @keydown.space="toggleOption(id)"
              @keydown.enter="toggleOption(id)"
              @click="toggleOption(id)"
            >
              <BaseCheckbox
                class="option__checkbox"
                :id="`status-${id}`"
                :checked="isSelected(id)"
                :disabled="false"
                @change="toggleOption(id)"
              />
              <label 
                :for="`status-${id}`"
                class="option__label"
                :style="{ color: color.value }"
              >
                {{ name }}
              </label>
            </li>
          </ul>
        </div>
      </span>
    </BaseDropdown>
  </div>
</template>

<script>
import { RecordStatus } from "~/v1/domain/entities/record/RecordStatus";

export default {
  props: {
    selectedOptions: {
      type: Array,
      default: () => [],
    },
  },
  model: {
    prop: "selectedOptions",
    event: "change",
  },
  data() {
    return {
      dropdownIsVisible: false,
      options: [
        {
          id: RecordStatus.pending.name,
          name: this.$tc(`recordStatus.${RecordStatus.pending.name}`, 1),
          color: RecordStatus.pending.color,
        },
        {
          id: RecordStatus.draft.name,
          name: this.$tc(`recordStatus.${RecordStatus.draft.name}`, 1),
          color: RecordStatus.draft.color,
        },
        {
          id: RecordStatus.discarded.name,
          name: this.$tc(`recordStatus.${RecordStatus.discarded.name}`, 1),
          color: RecordStatus.discarded.color,
        },
        {
          id: RecordStatus.submitted.name,
          name: this.$tc(`recordStatus.${RecordStatus.submitted.name}`, 1),
          color: RecordStatus.submitted.color,
        },
      ],
    };
  },
  computed: {
    displayText() {
      if (!this.selectedOptions.length) {
        return this.$t('allStatuses');
      }
      if (this.selectedOptions.length === 1) {
        const option = this.options.find(opt => opt.id === this.selectedOptions[0]);
        return option ? option.name : this.$t('status');
      }
      return this.$t('multipleStatuses', { count: this.selectedOptions.length });
    },
    hasSelections() {
      return this.selectedOptions.length > 0;
    }
  },
  methods: {
    onVisibility(visible) {
      this.dropdownIsVisible = visible;
    },
    isSelected(statusId) {
      return this.selectedOptions.includes(statusId);
    },
    toggleOption(statusId) {
      const currentSelections = [...this.selectedOptions];
      const index = currentSelections.indexOf(statusId);
      
      if (index > -1) {
        currentSelections.splice(index, 1);
      } else {
        currentSelections.push(statusId);
      }
      
      this.$emit("change", currentSelections);
    },
    clearAll() {
      this.$emit("change", []);
    },
  },
};
</script>

<style lang="scss" scoped>
.filter-multi-status {
  flex-shrink: 0;
}

.multi-status-options {
  padding: $base-space;
  min-width: 200px;
}

.multi-status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $base-space;
  padding-bottom: $base-space * 0.5;
  border-bottom: 1px solid palette(grey, 600);
}

.multi-status-title {
  font-weight: 600;
  margin: 0;
  color: palette(grey, 100);
}

.clear-all-btn {
  font-size: 0.875rem;
  padding: $base-space * 0.25 $base-space * 0.5;
  background: transparent;
  color: palette(blue, 400);
  border: 1px solid palette(blue, 400);
  border-radius: 4px;
  
  &:hover {
    background: palette(blue, 400);
    color: white;
  }
}

.options {
  list-style: none;
  margin: 0;
  padding: 0;
}

.option {
  display: flex;
  align-items: center;
  padding: $base-space * 0.5;
  cursor: pointer;
  border-radius: 4px;
  
  &:hover {
    background: palette(grey, 700);
  }
  
  &.selected {
    background: palette(grey, 600);
  }
}

.option__checkbox {
  margin-right: $base-space * 0.5;
}

.option__label {
  font-weight: 500;
  cursor: pointer;
  flex: 1;
}
</style>