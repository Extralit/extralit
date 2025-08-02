<template>
  <div ref="tabulator" class="tabulator-container" />
</template>

<script lang="ts">
import { TabulatorFull as Tabulator, ColumnDefinition, CellComponent, RowComponent } from "tabulator-tables";
import "tabulator-tables/dist/css/tabulator_semanticui.min.css";

export default {
  name: "BaseSimpleTable",

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

    processedColumns() {
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
  },

  watch: {
    data: {
      handler(newData) {
        if (this.tabulator && this.isInitialized) {
          this.tabulator.setData(newData);
        }
      },
      deep: true,
    },

    columns: {
      handler() {
        if (this.tabulator && this.isInitialized) {
          this.tabulator.setColumns(this.processedColumns);
        }
      },
      deep: true,
    },

    loading(newLoading) {
      if (this.tabulator && this.isInitialized) {
        if (newLoading) {
          this.tabulator.blockRedraw();
        } else {
          this.tabulator.restoreRedraw();
        }
      }
    },
  },

  mounted() {
    this.initializeTable();
  },

  beforeDestroy() {
    if (this.tabulator) {
      this.tabulator.destroy();
      this.tabulator = null;
    }
  },

  methods: {
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

    // Public API methods
    getData() {
      return this.tabulator ? this.tabulator.getData() : [];
    },

    getSelectedData() {
      return this.tabulator ? this.tabulator.getSelectedData() : [];
    },

    getSelectedRows() {
      return this.tabulator ? this.tabulator.getSelectedRows() : [];
    },

    selectRow(rows) {
      if (this.tabulator) {
        this.tabulator.selectRow(rows);
      }
    },

    deselectRow(rows) {
      if (this.tabulator) {
        this.tabulator.deselectRow(rows);
      }
    },

    addRow(data, pos, index) {
      if (this.tabulator) {
        return this.tabulator.addRow(data, pos, index);
      }
      return Promise.reject(new Error("Table not initialized"));
    },

    updateRow(row, data) {
      if (this.tabulator) {
        return this.tabulator.updateRow(row, data);
      }
      return false;
    },

    deleteRow(rows) {
      if (this.tabulator) {
        this.tabulator.deleteRow(rows);
      }
    },

    clearData() {
      if (this.tabulator) {
        this.tabulator.clearData();
      }
    },

    setData(data) {
      if (this.tabulator) {
        return this.tabulator.setData(data);
      }
      return Promise.resolve();
    },

    setFilter(field, type, value) {
      if (this.tabulator) {
        this.tabulator.setFilter(field, type, value);
      }
    },

    clearFilter(includeHeaderFilters) {
      if (this.tabulator) {
        this.tabulator.clearFilter(includeHeaderFilters);
      }
    },

    setSort(sortList) {
      if (this.tabulator) {
        this.tabulator.setSort(sortList);
      }
    },

    clearSort() {
      if (this.tabulator) {
        this.tabulator.clearSort();
      }
    },

    redraw(force) {
      if (this.tabulator) {
        this.tabulator.redraw(force);
      }
    },

    scrollToRow(row, position, ifVisible) {
      if (this.tabulator) {
        return this.tabulator.scrollToRow(row, position, ifVisible);
      }
      return Promise.resolve();
    },

    scrollToColumn(column, position, ifVisible) {
      if (this.tabulator) {
        return this.tabulator.scrollToColumn(column, position, ifVisible);
      }
      return Promise.resolve();
    },

    download(downloadType, filename, options) {
      if (this.tabulator) {
        this.tabulator.download(downloadType, filename, options);
      }
    },

    // Utility methods
    getRowCount() {
      return this.tabulator ? this.tabulator.getDataCount() : 0;
    },

    getColumns() {
      return this.tabulator ? this.tabulator.getColumns() : [];
    },

    hideColumn(column) {
      if (this.tabulator) {
        this.tabulator.hideColumn(column);
      }
    },

    showColumn(column) {
      if (this.tabulator) {
        this.tabulator.showColumn(column);
      }
    },

    toggleColumn(column) {
      if (this.tabulator) {
        this.tabulator.toggleColumn(column);
      }
    },
  },
};
</script>

<style lang="scss" scoped>
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
</style>
