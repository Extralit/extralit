<template>
  <div class="table_field_component">
    <div class="title-area --body2">
      <span class="table_field_component__title-content" v-text="title" />
    </div>
    <RenderTable
      :tableData="fieldContent"
      :editable="false"
    />
  </div>
</template>

<script lang="ts">
import RenderTable from '@/components/base/base-render-table/RenderTable.vue';

export default {
  name: 'TableField',
  components: {
    RenderTable,
  },
  props: {
    name: {
      type: String,
      required: true,
    },
    title: {
      type: String,
    },
    value: {
      type: [Object, String],
      required: true,
    },
  },
  computed: {
    fieldContent(): string {
      // If content is an object, stringify it for RenderTable
      if (typeof this.content === 'object') {
        return JSON.stringify(this.content);
      }
      return this.content;
    },
  },
};
</script>

<style lang="scss" scoped>
.table_field_component {
  display: flex;
  flex-direction: column;
  gap: $base-space;
  padding: 2 * $base-space;
  background: var(--bg-field);
  border-radius: $border-radius-m;
  border: 1px solid var(--border-field);

  &__title-content {
    word-break: break-word;
    width: calc(100% - 30px);
    color: var(--fg-secondary);
  }
}
</style>