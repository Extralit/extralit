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
  <div class="record-groups" v-if="recordsByReference.size > 0">
    <div 
      v-for="[reference, records] in recordsByReference" 
      :key="reference"
      class="record-group"
      :class="{ 'multiple-groups': hasMultipleGroups }"
    >
      <div 
        v-if="hasMultipleGroups" 
        class="group-header"
      >
        <div class="group-reference">
          <svgicon
            name="document"
            width="16"
            height="16"
            class="reference-icon"
          />
          <span class="reference-text">{{ formatReference(reference) }}</span>
          <span class="record-count">({{ records.length }} {{ $tc('record', records.length) }})</span>
        </div>
        <div class="group-actions">
          <BaseButton
            v-if="!isGroupExpanded(reference)"
            class="expand-btn small"
            @click="expandGroup(reference)"
          >
            {{ $t('expandGroup') }}
          </BaseButton>
          <BaseButton
            v-else
            class="collapse-btn small"
            @click="collapseGroup(reference)"
          >
            {{ $t('collapseGroup') }}
          </BaseButton>
        </div>
      </div>
      
      <div 
        class="group-records"
        :class="{ 
          'collapsed': hasMultipleGroups && !isGroupExpanded(reference),
          'expanded': hasMultipleGroups && isGroupExpanded(reference)
        }"
      >
        <slot 
          :records="records"
          :reference="reference"
          :isGrouped="hasMultipleGroups"
        ></slot>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "RecordGroups",
  props: {
    records: {
      type: Object,
      required: true,
    },
    autoExpandSingleGroup: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {
      expandedGroups: new Set(),
    };
  },
  computed: {
    recordsByReference() {
      return this.records.recordsByReference;
    },
    hasMultipleGroups() {
      return this.records.hasMultipleReferences;
    },
  },
  methods: {
    formatReference(reference) {
      if (reference === 'unknown') {
        return this.$t('unknownReference');
      }
      // Truncate long references for display
      return reference.length > 30 ? `${reference.substring(0, 30)}...` : reference;
    },
    isGroupExpanded(reference) {
      // Auto-expand if only one group and autoExpandSingleGroup is true
      if (!this.hasMultipleGroups && this.autoExpandSingleGroup) {
        return true;
      }
      return this.expandedGroups.has(reference);
    },
    expandGroup(reference) {
      this.expandedGroups.add(reference);
    },
    collapseGroup(reference) {
      this.expandedGroups.delete(reference);
    },
    expandAll() {
      this.recordsByReference.forEach((_, reference) => {
        this.expandedGroups.add(reference);
      });
    },
    collapseAll() {
      this.expandedGroups.clear();
    },
  },
  mounted() {
    // Auto-expand the first group if there are multiple groups
    if (this.hasMultipleGroups && this.recordsByReference.size > 0) {
      const firstReference = this.recordsByReference.keys().next().value;
      this.expandedGroups.add(firstReference);
    }
  },
};
</script>

<style lang="scss" scoped>
.record-groups {
  width: 100%;
}

.record-group {
  margin-bottom: $base-space;
  
  &:last-child {
    margin-bottom: 0;
  }
  
  &.multiple-groups {
    border: 1px solid palette(grey, 600);
    border-radius: 8px;
    overflow: hidden;
  }
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $base-space;
  background: palette(grey, 700);
  border-bottom: 1px solid palette(grey, 600);
}

.group-reference {
  display: flex;
  align-items: center;
  gap: $base-space * 0.5;
  flex: 1;
}

.reference-icon {
  color: palette(blue, 400);
  flex-shrink: 0;
}

.reference-text {
  font-weight: 600;
  color: palette(grey, 100);
  font-family: monospace;
  font-size: 0.9rem;
}

.record-count {
  color: palette(grey, 300);
  font-size: 0.875rem;
  margin-left: $base-space * 0.5;
}

.group-actions {
  display: flex;
  gap: $base-space * 0.5;
}

.expand-btn,
.collapse-btn {
  background: transparent;
  border: 1px solid palette(blue, 400);
  color: palette(blue, 400);
  padding: $base-space * 0.25 $base-space * 0.5;
  font-size: 0.75rem;
  
  &:hover {
    background: palette(blue, 400);
    color: white;
  }
}

.group-records {
  &.collapsed {
    display: none;
  }
  
  &.expanded {
    display: block;
  }
  
  // When not grouped (single reference), always show
  &:not(.collapsed):not(.expanded) {
    display: block;
  }
}

// Style adjustments for grouped vs ungrouped display
.record-group.multiple-groups .group-records {
  padding: $base-space;
}
</style>