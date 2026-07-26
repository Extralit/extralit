<template>
  <table class="v2-records-table">
    <thead>
      <tr>
        <th v-text="$t('schemas.reference')" />
        <th v-for="column in columns" :key="column.name">{{ column.name }}</th>
        <th v-text="$t('schemas.status')" />
      </tr>
    </thead>
    <tbody>
      <tr v-for="record in records" :key="record.id">
        <td>
          <span :data-reference="record.reference">{{ record.reference }}</span>
        </td>
        <td v-for="column in columns" :key="column.name">{{ formatCell(record.fields[column.name]) }}</td>
        <td><V2StatusBadge :status="record.status" /></td>
      </tr>
    </tbody>
  </table>
</template>

<script lang="ts">
import { type PropType } from "vue";
import { type V2Record } from "~/v2/domain/entities/record/V2Record";
import { type ColumnMeta } from "~/v2/domain/entities/schema/ColumnMeta";

export default {
  props: {
    records: { type: Array as PropType<V2Record[]>, required: true },
    columns: { type: Array as PropType<ColumnMeta[]>, required: true },
  },
  methods: {
    formatCell(value: unknown): string {
      if (value === null || value === undefined) return "—";
      if (typeof value === "object") return JSON.stringify(value);
      return String(value);
    },
  },
};
</script>

<style lang="scss" scoped>
.v2-records-table {
  width: 100%;
  border-collapse: collapse;

  th,
  td {
    text-align: left;
    padding: $base-space;
    border-bottom: 1px solid var(--bg-opacity-10);
    max-width: 320px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>
