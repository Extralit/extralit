<template>
  <div class="table-container">
    <div ref="table" class="--table" />

    <div class="--buttons">
      <button v-show="indexColumns?.length" @click.prevent="toggleColumnFreeze">⬅️ Toggle column freeze</button>
      <button @click.prevent="validateTable({ showErrors: true, scrollToError: true })">✅ Validate</button>
      <button v-show="editable" @click.prevent="addColumn">➕ Add column</button>
      <button v-show="editable" @click.prevent="addRow">➕ Add row</button>
    </div>
  </div>
</template>

<script>
import {
  TabulatorFull as Tabulator,
  MoveColumnsModule,
} from "tabulator-tables";
import "tabulator-tables/dist/css/tabulator.min.css";

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
      freezeColumns: true,
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
    columnValidators() {
      const tableColumns = this.tableJSON.schema.fields.map((col) => col.name);
      const schemaColumns = this.tableJSON.validation?.columns; // Pandera yaml schema
      if (schemaColumns === null) return {};

      var integer = (cell, value, parameters) => value == "NA" || Number.isInteger(parseInt(value));
      var decimal = (cell, value, parameters) => value == "NA" || !isNaN(parseFloat(value));
      var greater_equal = (cell, value, parameters) => value == "NA" || parseFloat(value) >= parameters;
      var less_equal = (cell, value, parameters) => value == "NA" || parseFloat(value) <= parameters;

      const tabulatorValidators = {};
      for (const [columnName, columnSchema] of Object.entries(schemaColumns)) {
        if (!tableColumns.includes(columnName)) continue;

        const validators = [];

        if (columnSchema.nullable === false) {
          validators.push("required");
        }

        if (columnSchema.dtype === "str") {
          validators.push("string");
        } else if (columnSchema.dtype.includes("int")) {
          validators.push({ type: integer, parameters: null });
        } else if (columnSchema.dtype.includes("float")) {
          validators.push({ type: decimal, parameters: null });
        }

        for (const key in columnSchema?.checks) {
          const value = columnSchema.checks[key];

          if (key === "greater_than_or_equal_to") {
            validators.push({ type: greater_equal, parameters: value });
          } else if (key === "less_than_or_equal_to") {
            validators.push({ type: less_equal, parameters: value });
          } else if (key === "isin" && value.length) {
            validators.push(`in:${[...value, "NA"].join("|")}`);
          }
        }

        // Custom validator example for unique check
        if (columnSchema.unique) {
          const uniqueValidator = {
            type: function (cell, value, parameters) {
              const columnValues = cell
                .getTable()
                .getData()
                .map((row) => row[cell.getField()]);
              return columnValues.filter((v) => v === value).length === 1;
            },
          };
          validators.push(uniqueValidator);
        }
        tabulatorValidators[columnName] = validators;
      }

      return tabulatorValidators;
    },
  },
  methods: {
    getColumnEditableConfig(fieldName) {
      if (!this.editable || this.indexColumns.includes(fieldName)) return {};

      // Default editable config for a column
      var config = {
        editor: "input",
        editorParams: {
          selectContents: true,
          search: true,
          emptyValue: "NA",
          autocomplete: true,
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
          this.tableJSON.data = this.table.getData();
          this.validateTable();
          this.tableJSON = this.tableJSON; // Trigger the setter
        },
      };

      // Add custom editor params for a column based on the Pandera validation schema
      if (this.tableJSON.validation?.columns?.hasOwnProperty(fieldName)) {
        const columnSchema = this.tableJSON.validation?.columns[fieldName];

        for (const key in columnSchema?.checks) {
          var values = columnSchema.checks[key];
          if (key === "isin" && values.length) {
            config.editor = "list";
            config.editorParams.values = values;
            config.editorParams.autocomplete = true;
            config.editorParams.listOnEmpty = true;
            config.editorParams.freetext = true;
          }
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
        this.table.scrollToColumn(firstErrorCell._cell.column.field);
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
      const rowColumns = Object.keys(row?._row.data);
      // Ensures only to highlight on tables with the same columns
      if (
        rowColumns.length !== this.columns.length ||
        !rowColumns.every((val) => this.columns.includes(val))
      )
        return;

      // const selectedRow = this.table.getRows()[pos - 1]
      const selectedRow = this.table
        .getRows()
        .find(
          (tableRow) =>
            JSON.stringify(tableRow.getData()) === JSON.stringify(row._row.data)
        );
      if (selectedRow === undefined) return;

      // Only highlight if the row is not already selected
      if (this.table.getSelectedRows().indexOf(selectedRow) != -1) return;
      // this.table.scrollToRow(selectedRow, null, false);
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
      this.tableJSON = this.tableJSON; // Trigger the setter

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
        var desc = this.tableJSON?.schema?.fields?.find(
          (col) => col.name === fieldName
        )?.description;

        if (this.tableJSON?.validation?.columns.hasOwnProperty(fieldName)) {
          const panderaSchema = this.tableJSON?.validation.columns[fieldName];
          desc = panderaSchema.description;

          if (this.columnValidators.hasOwnProperty(fieldName)) {
            const stringAndFunctionNames = this.columnValidators[fieldName]
              .map((value) => {
                if (typeof value === "string") {
                  return value;
                } else if (typeof value === "function") {
                  return value.name;
                } else if (typeof value === "object" && value?.type?.name) {
                  return value?.parameters != null
                    ? `${value.type.name}: ${value.parameters}`
                    : `${value.type.name}`;
                }
              })
              .filter((value) => value !== undefined);
            desc += `<br/><br/>Checks: ${stringAndFunctionNames}`
              .replace(/,/g, ", ")
              .replace(/:/g, ": ");
          }
        }

        if (!desc) return null;
        return desc;
      } catch (error) {
        console.log(error);
        // print stack trace
        console.log(error.stack);
      }
    },
  },
  mounted() {
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
