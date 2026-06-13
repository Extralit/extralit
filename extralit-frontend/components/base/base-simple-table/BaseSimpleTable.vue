<template>
  <div :class="['tabulator-container', 'tabulator-container--simple', { 'tabulator-container--editable': editable }]">
    <RenderTable
      ref="renderTable"
      :tableJSON="computedTableJSON"
      :editable="editable"
      :hasValidValues="hasValidValues"
      :questions="questions"
      :validation="validation || validators"
      @table-built="$emit('table-built')"
      @row-click="(e, row) => $emit('row-click', e, row)"
      @cell-edited="(cell) => $emit('cell-edited', cell)"
      @updateValidValues="(value) => $emit('updateValidValues', value)"
    />
  </div>
</template>

<script lang="ts">
import RenderTable from "~/components/base/base-render-table/RenderTable.vue";
import "tabulator-tables/dist/css/tabulator.min.css";
import { TableData } from "@/v1/domain/entities/table/TableData";
import { DataFrameSchema } from "@/v1/domain/entities/table/Schema";
import { Question } from "@/v1/domain/entities/question/Question";
import { type Validators } from "@/v1/domain/entities/table/Validation";

export default {
  name: "BaseSimpleTable",

  components: {
    RenderTable,
  },

  props: {
    data: {
      type: Array,
      default: () => [],
    },
    columns: {
      type: Array,
      required: true,
    },
    options: {
      type: Object,
      default: () => ({}),
    },
    loading: {
      type: Boolean,
      default: false,
    },
    editable: {
      type: Boolean,
      default: false,
    },
    validation: {
      type: Object,
      default: null,
    },
    validators: {
      type: Object as () => Validators,
      default: null,
    },
    hasValidValues: {
      type: Boolean,
      default: false,
    },
    questions: {
      type: Array as () => Question[],
      default: () => [],
    },
  },

  computed: {
    // Convert simple data/columns to TableData format for RenderTable
    computedTableJSON(): TableData {
      // FIX 1: Use "...col" to preserve editor config (dropdowns), validators, and freezing
      const fields = this.columns.map((col: any) => ({
        name: col.field,
        type: col.type || "string",
        ...col // <--- THIS IS THE MAGIC FIX
      }));

      const schema = new DataFrameSchema(
        fields,
        [],
        null,
        "simple-table"
      );

      const tableData = new TableData(
        [...this.data] as any[],
        schema,
        null
      );

      // FIX 2: Handle both 'validation' and 'validators' props
      // ImportFileUpload passes :validators, so we must prioritize that.
      if (this.validators) {
        // We wrap it in a structure RenderTable understands
        tableData.validation = { columns: {}, ...this.validation };
        // We might need to pass this directly to the RenderTable prop instead,
        // but attaching it to tableData is the safest way for the Schema to know about it.
      } else if (this.validation) {
        tableData.validation = this.validation;
      }

      return tableData;
    },
  },

  methods: {
    // Public API methods - delegate to internal RenderTable's tabulator
    getInternalTabulator() {
      return this.$refs.renderTable?.tabulator;
    },

    getData() {
      const tabulator = this.getInternalTabulator();
      return tabulator ? tabulator.getData() : [];
    },

    setData(data: any[]) {
      const tabulator = this.getInternalTabulator();
      if (tabulator) {
        return tabulator.setData(data);
      }
      return Promise.resolve();
    },

    getRowCount() {
      const tabulator = this.getInternalTabulator();
      return tabulator ? tabulator.getDataCount() : 0;
    },

    getColumns() {
      const tabulator = this.getInternalTabulator();
      return tabulator ? tabulator.getColumns() : [];
    },

    validateTable(options?: { scrollToError?: boolean; saveData?: boolean }) {
      if (this.$refs.renderTable?.validateTable) {
        return this.$refs.renderTable.validateTable(options);
      }
      return true;
    },

    redraw(force?: boolean) {
      const tabulator = this.getInternalTabulator();
      if (tabulator) {
        tabulator.redraw(force);
      }
    },
  },
};
</script>

<style lang="scss">
// Styles for BaseSimpleTable wrapping RenderTable
.tabulator-container--simple {
  display: flex;
  flex-flow: column;
  position: relative;
  max-height: 80vh;
  border: 1px solid var(--border-field);
  border-radius: $border-radius;
  background: var(--bg-accent-grey-1);
  overflow: auto;

  // Force light-mode colors regardless of [data-theme]
  --bg-solid-grey-1: hsl(0, 0%, 98%);
  --bg-solid-grey-2: hsl(0, 0%, 96%);
  --bg-solid-grey-3: hsl(0, 0%, 90%);
  --bg-solid-grey-4: hsl(0, 0%, 90%);
  --bg-accent-grey-1: hsl(0, 0%, 100%);
  --bg-accent-grey-2: hsl(0, 0%, 100%);
  --bg-accent-grey-3: hsl(0, 0%, 98%);
  --bg-accent-grey-4: hsl(0, 0%, 98%);
  --bg-accent-grey-5: hsl(0, 0%, 100%);
  --fg-primary: hsla(0, 0%, 0%, 0.87);
  --fg-secondary: hsla(0, 0%, 0%, 0.54);
  --fg-tertiary: hsla(0, 0%, 0%, 0.37);
  --border-field: hsl(0, 0%, 94%);
  --bg-opacity-4: hsla(0, 0%, 0%, 0.04);

  // Hide RenderTable's edit buttons when not editable
  :deep(.table-container) {
    .__table-buttons {
      display: none;
    }
    max-height: inherit;
    margin-bottom: 0;
  }

  // Apply design system styling to RenderTable's tabulator
  :deep(.tabulator) {
    background: var(--bg-accent-grey-1);
    border: none;
    font-family: $primary-font-family;
    font-size: $base-font-size;

    .tabulator-header {
      background: var(--bg-solid-grey-2);
      border-bottom: 1px solid var(--border-field);

      .tabulator-col {
        background: var(--bg-solid-grey-2);
        border-right: 1px solid var(--border-field);

        .tabulator-col-content {
          color: var(--fg-primary);
          font-weight: 600;
          padding: $base-space;
        }

        &:hover {
          background: var(--bg-solid-grey-3);
        }
      }
    }

    .tabulator-tableHolder {
      background: var(--bg-accent-grey-1);

      .tabulator-table {
        background: var(--bg-accent-grey-1);

        .tabulator-row {
          background: var(--bg-accent-grey-1);
          border-bottom: 1px solid var(--bg-solid-grey-2);

          &:hover {
            background: var(--bg-solid-grey-2);
          }

          .tabulator-cell {
            color: var(--fg-primary);
            border-right: 1px solid var(--bg-solid-grey-2);
            padding: $base-space;
          }
        }

        .tabulator-row-odd {
          background: var(--bg-accent-grey-1);

          &:hover {
            background: var(--bg-solid-grey-2);
          }
        }

        .tabulator-row-even {
          background: var(--bg-accent-grey-2);

          &:hover {
            background: var(--bg-solid-grey-3);
          }
        }
      }
    }

    // Frozen column header — override Tabulator's hardcoded bg
    .tabulator-col.tabulator-frozen {
      background-color: var(--bg-solid-grey-2) !important;
      will-change: transform;
    }

    // Frozen body cells — prevent dark-bg inheritance
    .tabulator-row .tabulator-cell.tabulator-frozen,
    .tabulator-row-odd .tabulator-cell.tabulator-frozen {
      background-color: var(--bg-accent-grey-1) !important;
      will-change: transform;
    }

    .tabulator-row-even .tabulator-cell.tabulator-frozen {
      background-color: var(--bg-accent-grey-2) !important;
      will-change: transform;
    }
  }

  // When editable, show the buttons
  &.tabulator-container--editable {
    :deep(.table-container) {
      .__table-buttons {
        display: flex;
      }
    }
  }
}
</style>
