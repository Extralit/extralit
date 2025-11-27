<template>
  <!-- Use RenderTable when editable or tableJSON is provided -->
  <div v-if="useRenderTable" :class="['tabulator-container', 'tabulator-container--simple', { 'tabulator-container--editable': editable }]">
    <RenderTable
      ref="renderTable"
      :tableJSON="computedTableJSON"
      :editable="editable"
      :hasValidValues="hasValidValues"
      :questions="questions"
      @table-built="$emit('table-built')"
      @data-loaded="handleDataLoaded"
      @data-changed="handleDataChanged"
      @row-click="(e, row) => $emit('row-click', e, row)"
      @row-dblclick="(e, row) => $emit('row-dblclick', e, row)"
      @row-selected="(row) => $emit('row-selected', row)"
      @row-deselected="(row) => $emit('row-deselected', row)"
      @cell-edited="(cell) => $emit('cell-edited', cell)"
      @column-moved="(column, columns) => $emit('column-moved', column, columns)"
      @column-resized="(column) => $emit('column-resized', column)"
      @header-click="(e, column) => $emit('header-click', e, column)"
      @header-dblclick="(e, column) => $emit('header-dblclick', e, column)"
      @change-text="(text) => $emit('change-text', text)"
      @updateValidValues="(value) => $emit('updateValidValues', value)"
      @on-change-focus="(value) => $emit('on-change-focus', value)"
      @on-exit-edition-mode="$emit('on-exit-edition-mode')"
      @error="(error) => $emit('error', error)"
    />
  </div>
  <!-- Use simple Tabulator directly for read-only mode without tableJSON -->
  <div v-else ref="tabulator" class="tabulator-container" />
</template>

<script lang="ts">
import { TabulatorFull as Tabulator, ColumnDefinition, CellComponent, RowComponent } from "tabulator-tables";
import "tabulator-tables/dist/css/tabulator.min.css";
import RenderTable from "~/components/base/base-render-table/RenderTable.vue";
import { TableData, DataFrameSchema } from "@/v1/domain/entities/table/TableData";
import { Question } from "@/v1/domain/entities/question/Question";

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
    // New optional props for RenderTable compatibility
    editable: {
      type: Boolean,
      default: false,
    },
    validation: {
      type: Object,
      default: null,
    },
    tableJSON: {
      type: Object as () => TableData,
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

  data() {
    return {
      tabulator: null,
      isInitialized: false,
    };
  },

  computed: {
    tabulatorOptions() {
      const defaultOptions = {
        data: this.data,
        layout: "fitDataFill",
        maxHeight: "100%",
        renderHorizontal: "virtual",
        resizableColumns: true,
        movableColumns: false,
        movableRows: false,
        selectable: false,
        pagination: false,
        paginationSize: 20,
        paginationSizeSelector: [10, 20, 50, 100],
        sortMode: "local",
        filterMode: "local",
        placeholder: "No data available",
        tooltipsHeader: true,
        tooltips: true,
        columnDefaults: {
          resizable: true,
          tooltip: true,
        },
      };

      return {
        ...defaultOptions,
        ...this.options,
        columns: this.processedColumns,
      };
    },

    processedColumns(): ColumnDefinition[] {
      return this.columns.map((col) => {
        const column: any = {
          field: col.field,
          title: col.title,
          headerSort: col.sortable !== false,
          resizable: col.resizable !== false,
          visible: col.visible !== false,
        };

        // Set width properties
        if (col.width) column.width = col.width;
        if (col.minWidth) column.minWidth = col.minWidth;
        if (col.maxWidth) column.maxWidth = col.maxWidth;

        // Set formatter
        if (col.formatter) {
          column.formatter = col.formatter;
        }

        // Set editor
        if (col.editor !== undefined) {
          column.editor = col.editor;
          if (col.editorParams) {
            column.editorParams = col.editorParams;
          }
        }

        // Set validator
        if (col.validator) {
          column.validator = col.validator;
        }

        // Set header filter
        if (col.filterable || col.headerFilter) {
          column.headerFilter = col.headerFilter || "input";
          if (col.headerFilterParams) {
            column.headerFilterParams = col.headerFilterParams;
          }
        }

        // Set cell click handlers
        if (col.cellClick) {
          column.cellClick = col.cellClick;
        }
        if (col.cellDblClick) {
          column.cellDblClick = col.cellDblClick;
        }

        // Set CSS class
        if (col.cssClass) {
          column.cssClass = col.cssClass;
        }

        // Set frozen column
        if (col.frozen) {
          column.frozen = col.frozen;
        }

        return column;
      });
    },

    // Determine whether to use RenderTable internally
    useRenderTable(): boolean {
      return this.editable || this.tableJSON !== null;
    },

    // Convert simple data/columns to TableData format for RenderTable
    computedTableJSON(): TableData | null {
      // If tableJSON is explicitly provided, use it directly
      if (this.tableJSON) {
        // If validation is provided, merge it into the tableJSON
        if (this.validation && this.tableJSON) {
          return {
            ...this.tableJSON,
            validation: this.validation,
          };
        }
        return this.tableJSON;
      }

      // If not using RenderTable, no tableJSON needed
      if (!this.useRenderTable) {
        return null;
      }

      // Convert data/columns format to TableData format for RenderTable
      const fields = this.columns.map((col: any) => ({
        name: col.field,
        type: col.type || "string",
      }));

      const schema: DataFrameSchema = {
        fields,
        schemaName: "simple-table",
        primaryKey: [],
      };

      const tableData: TableData = {
        schema,
        data: [...this.data] as any[],
        validation: this.validation,
      };

      return tableData;
    },
  },

  watch: {
    data: {
      handler(newData) {
        if (!this.useRenderTable && this.tabulator && this.isInitialized) {
          this.tabulator.setData(newData);
        }
      },
      deep: true,
    },

    columns: {
      handler() {
        if (!this.useRenderTable && this.tabulator && this.isInitialized) {
          this.tabulator.setColumns(this.processedColumns);
        }
      },
      deep: true,
    },

    loading(newLoading) {
      if (!this.useRenderTable && this.tabulator && this.isInitialized) {
        if (newLoading) {
          this.tabulator.blockRedraw();
        } else {
          this.tabulator.restoreRedraw();
        }
      }
    },
  },

  mounted() {
    if (!this.useRenderTable) {
      this.initializeTable();
    }
  },

  beforeDestroy() {
    if (!this.useRenderTable && this.tabulator) {
      this.tabulator.destroy();
      this.tabulator = null;
    }
  },

  methods: {
    // Event handlers for RenderTable
    handleDataLoaded(data: any) {
      this.$emit("data-loaded", data);
    },

    handleDataChanged(data: any) {
      this.$emit("data-changed", data);
    },

    initializeTable() {
      try {
        this.tabulator = new Tabulator(this.$refs.tabulator, {
          ...this.tabulatorOptions,
          // Event handlers
          tableBuilt: () => {
            this.isInitialized = true;
            this.$emit("table-built");
          },
          dataLoaded: (data) => {
            this.$emit("data-loaded", data);
          },
          dataChanged: (data) => {
            this.$emit("data-changed", data);
          },
          rowClick: (e, row) => {
            this.$emit("row-click", e, row);
          },
          rowDblClick: (e, row) => {
            this.$emit("row-dblclick", e, row);
          },
          rowSelected: (row) => {
            this.$emit("row-selected", row);
          },
          rowDeselected: (row) => {
            this.$emit("row-deselected", row);
          },
          cellEdited: (cell) => {
            this.$emit("cell-edited", cell);
          },
          columnMoved: (column, columns) => {
            this.$emit("column-moved", column, columns);
          },
          columnResized: (column) => {
            this.$emit("column-resized", column);
          },
          headerClick: (e, column) => {
            this.$emit("header-click", e, column);
          },
          headerDblClick: (e, column) => {
            this.$emit("header-dblclick", e, column);
          },
        });
      } catch (error) {
        console.error("Failed to initialize Tabulator:", error);
        this.$emit("error", error);
      }
    },

    // Public API methods - delegate to internal tabulator instance
    getInternalTabulator() {
      if (this.useRenderTable) {
        return this.$refs.renderTable?.tabulator;
      }
      return this.tabulator;
    },

    getData() {
      const tabulator = this.getInternalTabulator();
      return tabulator ? tabulator.getData() : [];
    },

    getSelectedData() {
      const tabulator = this.getInternalTabulator();
      return tabulator ? tabulator.getSelectedData() : [];
    },

    getSelectedRows() {
      const tabulator = this.getInternalTabulator();
      return tabulator ? tabulator.getSelectedRows() : [];
    },

    selectRow(rows) {
      const tabulator = this.getInternalTabulator();
      if (tabulator) {
        tabulator.selectRow(rows);
      }
    },

    deselectRow(rows) {
      const tabulator = this.getInternalTabulator();
      if (tabulator) {
        tabulator.deselectRow(rows);
      }
    },

    addRow(data, pos, index) {
      const tabulator = this.getInternalTabulator();
      if (tabulator) {
        return tabulator.addRow(data, pos, index);
      }
      return Promise.reject(new Error("Table not initialized"));
    },

    updateRow(row, data) {
      const tabulator = this.getInternalTabulator();
      if (tabulator) {
        return tabulator.updateRow(row, data);
      }
      return false;
    },

    deleteRow(rows) {
      const tabulator = this.getInternalTabulator();
      if (tabulator) {
        tabulator.deleteRow(rows);
      }
    },

    clearData() {
      const tabulator = this.getInternalTabulator();
      if (tabulator) {
        tabulator.clearData();
      }
    },

    setData(data) {
      const tabulator = this.getInternalTabulator();
      if (tabulator) {
        return tabulator.setData(data);
      }
      return Promise.resolve();
    },

    setFilter(field, type, value) {
      const tabulator = this.getInternalTabulator();
      if (tabulator) {
        tabulator.setFilter(field, type, value);
      }
    },

    clearFilter(includeHeaderFilters) {
      const tabulator = this.getInternalTabulator();
      if (tabulator) {
        tabulator.clearFilter(includeHeaderFilters);
      }
    },

    setSort(sortList) {
      const tabulator = this.getInternalTabulator();
      if (tabulator) {
        tabulator.setSort(sortList);
      }
    },

    clearSort() {
      const tabulator = this.getInternalTabulator();
      if (tabulator) {
        tabulator.clearSort();
      }
    },

    redraw(force) {
      const tabulator = this.getInternalTabulator();
      if (tabulator) {
        tabulator.redraw(force);
      }
    },

    scrollToRow(row, position, ifVisible) {
      const tabulator = this.getInternalTabulator();
      if (tabulator) {
        return tabulator.scrollToRow(row, position, ifVisible);
      }
      return Promise.resolve();
    },

    scrollToColumn(column, position, ifVisible) {
      const tabulator = this.getInternalTabulator();
      if (tabulator) {
        return tabulator.scrollToColumn(column, position, ifVisible);
      }
      return Promise.resolve();
    },

    download(downloadType, filename, options) {
      const tabulator = this.getInternalTabulator();
      if (tabulator) {
        tabulator.download(downloadType, filename, options);
      }
    },

    // Utility methods
    getRowCount() {
      const tabulator = this.getInternalTabulator();
      return tabulator ? tabulator.getDataCount() : 0;
    },

    getColumns() {
      const tabulator = this.getInternalTabulator();
      return tabulator ? tabulator.getColumns() : [];
    },

    hideColumn(column) {
      const tabulator = this.getInternalTabulator();
      if (tabulator) {
        tabulator.hideColumn(column);
      }
    },

    showColumn(column) {
      const tabulator = this.getInternalTabulator();
      if (tabulator) {
        tabulator.showColumn(column);
      }
    },

    toggleColumn(column) {
      const tabulator = this.getInternalTabulator();
      if (tabulator) {
        tabulator.toggleColumn(column);
      }
    },

    // Additional methods for RenderTable mode
    validateTable(options?: { scrollToError?: boolean; saveData?: boolean }) {
      if (this.useRenderTable && this.$refs.renderTable?.validateTable) {
        return this.$refs.renderTable.validateTable(options);
      }
      return true;
    },
  },
};
</script>

<style lang="scss">
.tabulator-container {
  display: flex;
  flex-flow: column;
  position: relative;
  max-height: 80vh;
  border: 1px solid var(--border-field);
  border-radius: $border-radius;
  background: var(--bg-accent-grey-1);
  overflow: auto;

  .__table {
    white-space: normal;
    position: relative;
    resize: vertical;
    overflow: auto;
  }
}

.tabulator-container {
  display: flex;
  flex-flow: column;
  position: relative;
  max-height: 80vh;
  border: 1px solid var(--border-field);
  border-radius: $border-radius;
  background: var(--bg-accent-grey-1);
  overflow: auto;

  .__table {
    white-space: normal;
    position: relative;
    resize: vertical;
    overflow: auto;
  }

  // Override Tabulator Semantic UI theme colors to match our design system
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

        &.tabulator-sortable {
          .tabulator-col-title {
            cursor: pointer;
          }
        }
      }

      .tabulator-col-resize-handle {
        background: var(--border-field);
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

          &.tabulator-selected {
            background: var(--bg-status-submitted);

            .tabulator-cell {
              color: var(--fg-status-submitted);
            }
          }

          .tabulator-cell {
            color: var(--fg-primary);
            border-right: 1px solid var(--bg-solid-grey-2);
            padding: $base-space;

            &.tabulator-editing {
              background: var(--bg-accent-grey-2);
              border: 2px solid var(--bg-action);
            }
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

    .tabulator-footer {
      background: var(--bg-solid-grey-2);
      border-top: 1px solid var(--border-field);
      color: var(--fg-secondary);

      .tabulator-page {
        background: var(--bg-accent-grey-1);
        border: 1px solid var(--border-field);
        color: var(--fg-primary);
        margin: 0 2px;

        &:hover {
          background: var(--bg-solid-grey-3);
        }

        &.tabulator-page-active {
          background: var(--bg-action);
          color: var(--fg-lighter);
        }
      }

      .tabulator-paginator {
        color: var(--fg-secondary);
      }
    }

    .tabulator-placeholder {
      background: var(--bg-accent-grey-1);
      color: var(--fg-secondary);
      text-align: center;
      padding: $base-space * 4;
      font-style: italic;
    }

    // Loading overlay
    .tabulator-loader {
      background: rgba(var(--bg-accent-grey-1), 0.8);

      .tabulator-loader-msg {
        background: var(--bg-accent-grey-1);
        border: 1px solid var(--border-field);
        color: var(--fg-primary);
        border-radius: $border-radius;
        padding: $base-space * 2;
      }
    }

    // Header filters
    .tabulator-header-filter {
      input {
        background: var(--bg-accent-grey-1);
        border: 1px solid var(--border-field);
        color: var(--fg-primary);
        border-radius: $border-radius-s;
        padding: 4px 8px;
        font-size: 12px;

        &:focus {
          border-color: var(--bg-action);
          outline: none;
        }
      }
    }
  }
}

// Styles for when wrapping RenderTable (--simple modifier)
.tabulator-container--simple {
  // Hide RenderTable's edit buttons when not editable
  :deep(.table-container) {
    .__table-buttons {
      display: none;
    }
  }

  // Apply clean simple styling to the wrapped RenderTable
  :deep(.table-container) {
    max-height: inherit;
    margin-bottom: 0;
  }

  // Apply same design system styling to RenderTable's tabulator
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
