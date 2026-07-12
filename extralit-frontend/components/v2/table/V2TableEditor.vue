<template>
  <div ref="tableEl" class="v2-table-editor" />
</template>

<script lang="ts">
import { defineComponent, onBeforeUnmount, onMounted, ref, watch, type PropType } from "vue";
import { TabulatorFull as Tabulator, type ColumnDefinition } from "tabulator-tables";
import "tabulator-tables/dist/css/tabulator.min.css";
import { ColumnMeta } from "~/v2/domain/entities/schema/ColumnMeta";
import { columnCellEditor, type CellEditor } from "~/v2/domain/entities/review/widget-mapping";

const EDITOR_BY_KIND: Record<CellEditor, ColumnDefinition["editor"]> = {
  text: "input",
  number: "number",
  checkbox: "tickCross",
  date: "date",
};

// Exported for unit tests (tabulator itself is mocked in vitest).
export const tabulatorColumns = (columns: ColumnMeta[], editable: boolean): ColumnDefinition[] =>
  columns.map((column) => ({
    title: column.name,
    field: column.name,
    // `false` disables editing at runtime; @types only types `editor` as `Editor | undefined`.
    editor: (editable ? EDITOR_BY_KIND[columnCellEditor(column)] : false) as ColumnDefinition["editor"],
    headerSort: false,
  }));

export const valueFromRowData = (rowData: Record<string, unknown>, columns: ColumnMeta[]): Record<string, unknown> => {
  const value: Record<string, unknown> = {};
  for (const column of columns) {
    if (rowData[column.name] !== undefined) value[column.name] = rowData[column.name];
  }
  return value;
};

export default defineComponent({
  name: "V2TableEditor",
  props: {
    modelValue: { type: Object as PropType<Record<string, unknown>>, required: true },
    columns: { type: Array as PropType<ColumnMeta[]>, required: true },
    editable: { type: Boolean, default: true },
  },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    const tableEl = ref<HTMLElement>();
    let tabulator: Tabulator | null = null;
    // Signature of the value we last emitted. When the parent echoes that same value
    // back into modelValue, skip the rebuild so we don't tear down the live editor
    // (losing focus/selection) on every committed cell edit. Flush-timing independent —
    // unlike a boolean flag reset synchronously before the async watcher fires.
    let lastEmittedSignature: string | null = null;

    const build = () => {
      tabulator?.destroy();
      tabulator = new Tabulator(tableEl.value!, {
        data: [{ ...props.modelValue }], // single-row grid: the value IS one dict
        columns: tabulatorColumns(props.columns, props.editable),
        layout: "fitDataStretch",
      });
      tabulator.on("cellEdited", (cell) => {
        const next = valueFromRowData(cell.getRow().getData(), props.columns);
        lastEmittedSignature = JSON.stringify(next);
        emit("update:modelValue", next);
      });
    };

    onMounted(build);
    onBeforeUnmount(() => tabulator?.destroy());

    // Column/editability changes always rebuild.
    watch(() => [props.columns, props.editable], build, { deep: true });

    // Value changes rebuild too (draft restore / discard) — except when the incoming
    // value is the echo of our own emit, which the live tabulator already reflects.
    watch(
      () => props.modelValue,
      () => {
        if (JSON.stringify(props.modelValue) === lastEmittedSignature) return;
        lastEmittedSignature = null;
        build();
      },
      { deep: true }
    );

    return { tableEl };
  },
});
</script>

<style lang="scss" scoped>
.v2-table-editor {
  width: 100%;
}
</style>
