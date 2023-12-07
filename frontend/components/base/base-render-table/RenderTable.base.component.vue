<template>
  <div class="table-container">
    <div ref="table" class="--table" />

    <div class="--buttons">
      <button v-show="indexColumns?.length" @click.prevent="toggleColumnFreeze">⬅️ Index</button>
      <button v-show="columns" @click.prevent="validateTable({ showErrors: true, scrollToError: true })">✅ Checks</button>
      <button v-show="editable" @click.prevent="addColumn">➕ Add column</button>
      <button v-show="editable" @click.prevent="addRow">➕ Add row</button>
      <button v-show="editable" @click.prevent="deleteRow">➖ Drop row</button>
    </div>
  </div>
</template>

<script>
import {
  TabulatorFull as Tabulator,
} from "tabulator-tables";
import "tabulator-tables/dist/css/tabulator.min.css";
import { getColumnValidators } from "./validationUtils";
import { columnSchemaToDesc } from "./tableUtils";

export default {
  name: "RenderTableBaseComponent",
  props: {
    tableData: {
      type: String,
      required: true,
    },
    editable: {
      type: Boolean,
      default: false,
    },
    hasValidValues: {
      type: Boolean,
      default: false,
    },
  },
  model: {
    prop: "hasValidValues",
    event: "updateValidValues",
  },
  data() {
    return {
      table: null,
      freezeColumns: false,
    };
  },
  computed: {
    tableJSON: {
      get() {
        try {
          return JSON.parse(this.tableData);
        } catch (error) {
          console.error("Failed to parse JSON:", error);
          return null;
        }
      },
      set(json) {
        this.$nuxt.$emit("on-update-response-tabledata", JSON.stringify(json));
      },
    },
    indexColumns() {
      return this.tableJSON?.schema?.primaryKey || [];
    },
    columns() {
      return this.table?.getColumns().map((col) => col.getField());
    },
    columnValidators() { 
      return getColumnValidators(this.tableJSON);
    },
    columnsConfig() {
      if (!this.tableJSON?.schema) return [];

      const configs = this.tableJSON.schema.fields.map((column, index) => ({
        title: column.name,
        field: column.name,
        frozen:
          this.freezeColumns &&
          this.indexColumns?.length &&
          this.indexColumns.includes(column.name),
        visible: column.name != "reference",
        validator: this.columnValidators.hasOwnProperty(column.name)
          ? this.columnValidators[column.name]
          : null,
        ...this.getColumnEditableConfig(column.name),
      }));

      // columns.unshift({ rowHandle: true, formatter: "handle", headerSort: false, frozen: true, width: 30, minWidth: 30 },);

      return configs;
    },
  },
  methods: {
    updateData() {
      this.tableJSON = this.table.getData();
      // eslint-disable-next-line no-self-assign
      this.tableJSON = this.tableJSON; // Trigger the setter
    },
    getColumnEditableConfig(fieldName) {
      if (!this.editable || this.indexColumns.includes(fieldName)) return {};

      // Default editable config for a column
      var config = {
        editor: "input",
        editorParams: {
          selectContents: true,
          search: true,
        },
        editableTitle: false,
        headerDblClick: (e, column) => {
          // Enable editable title on double click
          if (column.getDefinition().frozen) return;
          column.updateDefinition({
            editableTitle: !column.getDefinition().editableTitle,
          });
        },
        cellEdited: (cell) => {
          this.updateData();
          this.validateTable();
        },
      };

      // Add custom editor params for a column based on the Pandera validation schema
      if (this.tableJSON.validation?.columns?.hasOwnProperty(fieldName)) {
        const columnSchema = this.tableJSON.validation?.columns[fieldName];

        if (columnSchema.dtype === "str") {
          config.editor = "list";
          // config.editorParams.values = columnSchema.checks.isin;
          config.editorParams.defaultValue = "NA";
          config.editorParams.emptyValue = "NA";
          config.editorParams.valuesLookup = 'active';
          config.editorParams.valuesLookupField = fieldName;
          config.editorParams.autocomplete = true;
          config.editorParams.listOnEmpty = true;
          config.editorParams.freetext = true;
          config.editorParams.values = (columnSchema?.checks?.isin?.length) ? columnSchema.checks.isin : config.editorParams.values;
        }
      }
      return config;
    },
    validateTable(options) {
      var validErrors = this.table.validate();
      const isValid = validErrors === true;
      this.$emit("updateValidValues", isValid);
      if (isValid) return true;

      if (options?.scrollToError) {
        const firstErrorCell = validErrors[0];
        this.table.scrollToRow(firstErrorCell._cell.row);
        this.table.scrollToColumn(firstErrorCell._cell.column.field, 'middle');
      }

      if (options?.showErrors) {
        var errorValues = {};
        errorValues = validErrors.reduce((acc, cell) => {
          const failedChecks = cell.validate();
          acc[`${cell._cell.column.field}: ${cell._cell.value}`] = failedChecks;
          return acc;
        }, {});

        console.log("validateTable errors:", errorValues);
      }

      return isValid;
    },
    toggleColumnFreeze() {
      this.freezeColumns = !this.freezeColumns;
      this.table.setColumns(this.columnsConfig);
      this.validateTable();
    },
    columnMoved(column, columns) {
      this.tableJSON.schema.fields.sort((a, b) => {
        const aIndex = columns.findIndex((col) => col.getField() === a.name);
        const bIndex = columns.findIndex((col) => col.getField() === b.name);
        return aIndex - bIndex;
      });
      this.tableJSON = this.tableJSON; // Trigger the setter
    },
    clickRow(e, row) {
      row.toggleSelect();
      this.$nuxt.$emit("on-table-highlight-row", row);
    },
    selectRow(row) {
      // Highlight all rows with the same index accross different tables

      // const selectedRow = this.table.getRows()[pos - 1]
      const selectedRow = this.table
        .getRows()
        .find(
          (tableRow) => tableRow.getData().reference === row._row.data.reference
        );
      if (selectedRow === undefined) return;

      // Only highlight if the row is not already selected
      if (this.table.getSelectedRows().indexOf(selectedRow) != -1) return;
      this.table.scrollToRow(selectedRow, null, false);
      this.table.deselectRow("visible");
      this.table.toggleSelectRow(selectedRow._row);
    },
    addRow() {
      const selectedRows = this.table.getSelectedRows();
      if (selectedRows.length > 0) {
        const selectedRow = selectedRows[0];
        this.table.addRow({}, false, selectedRow);
      } else {
        this.table.addRow({}).then((row) => {
          row.validate();
        });
      }
    },
    deleteRow() {
      // Get the selected rows
      const selectedRows = this.table.getSelectedRows();

      // Delete each selected row from the table
      selectedRows.forEach((row) => {
        this.table.deleteRow(row);
      });

      // Update this.tableJSON to reflect the current data in the table
      this.updateData();
    },
    addColumn() {
      const newFieldName = "newColumn";

      this.table.addColumn({
        title: newFieldName,
        field: newFieldName,
        ...this.getColumnEditableConfig(newFieldName),
      }, true).then((col) => {
        this.validateTable();
      });

      // Add the new field to the schema
      const data = this.table.getData();
      data.forEach((item) => {
        item[newFieldName] = null;
      });
      this.table.setData(data);
      this.tableJSON.schema.fields.push({
        name: newFieldName,
        type: "string",
      });
      this.updateData();

      this.table.scrollToColumn(newFieldName, null, false);
    },
    columnTitleChanged(column) {
      const newFieldName = column.getDefinition().title.replace(/ /g, "_");
      const oldFieldName = column.getDefinition().field;

      // Update the field name for all data
      const data = this.table.getData();
      data.forEach((item) => {
        item[newFieldName] = item[oldFieldName];
        delete item[oldFieldName];
      });

      // Update the table data
      this.table.setData(data);
      this.tableJSON.data = data;

      this.table.updateColumnDefinition(column.getField(), {
        field: newFieldName,
      });

      // Update the field name in the schema
      this.tableJSON.schema.fields = this.tableJSON.schema.fields.map(
        (field) => {
          if (field.name === oldFieldName) {
            return { ...field, name: newFieldName };
          }
          return field;
        }
      );
      this.tableJSON = this.tableJSON; // Trigger the setter
      this.validateTable();

      this.table.scrollToColumn(newFieldName);
    },
    cellTooltip(e, cell, onRendered) {
      var text = cell.getValue();

      if (text?.length > 100) {
        return text;
      } else if (
        cell._cell?.column.field === "index" &&
        this.tableJSON?.validation.columns.hasOwnProperty(text)
      ) {
        const column_schema = this.tableJSON.validation.columns[text];
        return column_schema.description;
      }
      return null;
    },
    headerTooltip(e, column, onRendered) {
      try {
        const fieldName = column?.getDefinition()?.field;
        const desc = columnSchemaToDesc(fieldName, this.tableJSON, this.columnValidators)


        if (!desc) return null;
        return desc;
      } catch (error) {
        console.log(error);
        // print stack trace
        console.log(error.stack);
      }
    },
    async integrateReferencedData() {

    },
  },
  mounted() {
    if (!this.tableJSON) return;
    const layout =
      this.columnsConfig.length <= 2 ? "fitDataStretch" : "fitDataTable";

      this.table = new Tabulator(this.$refs.table, {
      maxHeight: "40vh",
      data: this.tableJSON.data,
      persistence: {
        columns: true,
      },
      reactiveData: true,
      clipboard: true,
      columnDefaults: {
        resizable: true,
        maxWidth: layout === "fitDataTable" ? 150 : null,
        headerWordWrap: true,
        headerSort: false,
        tooltip: this.cellTooltip.bind(this),
        headerTooltip: this.headerTooltip.bind(this),
      },
      columns: this.columnsConfig,
      index: this.columnsConfig.find((column) => column.field === "reference")
        ? "reference"
        : null,
      layout: layout,
      selectable: 1,
      selectablePersistence: true,
      validationMode: "highlight",
      movableColumns: this.editable,
      headerMenu: true,
    });
    this.table.on("rowClick", this.clickRow.bind(this));

    if (this.editable) {
      this.table.on("columnTitleChanged", this.columnTitleChanged.bind(this));
      this.table.on("columnMoved", this.columnMoved.bind(this));
    }

    this.table.on("tableBuilt", () => {
      this.toggleColumnFreeze();
    });

    this.$nuxt.$on("on-table-highlight-row", this.selectRow.bind(this));
  },
  beforeDestroy() {
    this.$nuxt.$off("on-table-highlight-row");
  },
};
</script>

<style scoped lang="scss">
.table-container {
  display: flex;
  flex-flow: column;
  position: relative;
  max-width: 100%;
  overflow: auto;
  // background: inherit;

  .--buttons {
    display: flex;
    justify-content: space-between;
    padding: 5px 5px 10px 0;
    color: white;
    border-radius: 5px;
    text-decoration: none;
  }

  .--table {
    overflow: auto;
    // overflow-x: auto;
  }
}
</style>
