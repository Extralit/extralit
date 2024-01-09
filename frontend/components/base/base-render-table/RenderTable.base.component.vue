<template>
  <div class="table-container">
    <div ref="table" class="--table" />

    <div class="--buttons">
      <button v-show="indexColumns && indexColumns.length" @click.prevent="toggleGroupRefColumns">
        ⬅️ References
      </button>
      <button v-show="columns && columnValidators && Object.keys(columnValidators).length" @click.prevent="validateTable({ showErrors: true, scrollToError: true })">
        ✅ Checks
      </button>
      <button v-show="editable" @click.prevent="addColumn">
        ➕ Add column
      </button>
      <button v-show="editable" @click.prevent="addRow">
        ➕ Add row
      </button>
      <button v-show="editable" @click.prevent="dropRow">
        ➖ Drop row
      </button>
    </div>
  </div>
</template>

<script>
import { TabulatorFull as Tabulator } from "tabulator-tables";
import "tabulator-tables/dist/css/tabulator.min.css";
import { getColumnValidators } from "./validationUtils";
import { 
  columnSchemaToDesc, 
  getTableDataFromRecords, 
  findMatchingRefValues,
  incrementReferenceStr,
  getMaxStringValue,
} from "./tableUtils"; 
import { del } from "vue";

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
      groupByRefColumns: true,
      isLoaded: false,
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
    refColumns() {
      try {
        const arr = this.tableJSON.schema.fields
          .map(field => field.name)
          .filter(name => typeof name === 'string' && name.endsWith('_ref'));
        return arr.length ? arr : null;
      } catch (error) {
        console.error("Failed to get refColumns:", error);
        return null;
      }
    },
    columns() {
      return this.table?.getColumns().map((col) => col.getField()) || [];
    },
    columnValidators() { 
      return getColumnValidators(this.tableJSON);
    },
    columnsConfig() {
      if (!this.tableJSON?.schema) return [];

      const configs = this.tableJSON.schema.fields.map((column) => {
        const visible = !this.groupByRefColumns || !this.isRefColumn(column.name);
        return {
          title: column.name,
          field: column.name,
          visible: visible,
          validator: this.columnValidators.hasOwnProperty(column.name)
            ? this.columnValidators[column.name]
            : null,
          ...this.getColumnEditableConfig(column.name),
        }
      });
      // configs.unshift({ rowHandle: true, formatter: "handle", headerSort: false, frozen: true, width: 30, minWidth: 30 },);
      return configs;
    },
    referenceValues() {
      if (!this.refColumns) return null;
      const firstRow = this.tableJSON?.data?.find((row) => row?.reference.includes('-'))
      if (!firstRow) return null;
      
      const refValues = this.refColumns.reduce((acc, refColumn, index) => {
        acc[refColumn] = firstRow[refColumn];
        return acc;
      }, {});
      if (!refValues) return null;
  
      const publication_ref = firstRow.reference.split('-')[0];

      let records = getTableDataFromRecords((record) => record?.metadata?.reference == publication_ref)
      const matchingRefValues = findMatchingRefValues(refValues, records)

      return matchingRefValues;
    },
  },
  methods: {
    updateTableJsonData() {
      this.tableJSON.data = this.table.getData();
      this.tableJSON = this.tableJSON; // Trigger the setter
    },
    isRefColumn(field) { 
      return field === "reference" || this.refColumns?.includes(field);
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
          this.updateTableJsonData();
          this.validateTable();
        },
      };

      if (!this.tableJSON.validation?.columns?.hasOwnProperty(fieldName)) return config;

      // Add custom editor params for a column based on the Pandera validation schema
      const columnSchema = this.tableJSON.validation?.columns[fieldName];

      if (columnSchema.dtype === "str") {
        config.editor = "list";
        config.editorParams.defaultValue = "NA";
        config.editorParams.emptyValue = "NA";
        config.editorParams.valuesLookup = 'active';
        config.editorParams.valuesLookupField = fieldName;
        config.editorParams.autocomplete = true;
        // config.editorParams.sort = (a, b) => a.length - b.length;
        // config.editorParams.multiselect = true;
        config.editorParams.listOnEmpty = true;
        config.editorParams.freetext = true;
        config.editorParams.values = (columnSchema.checks?.isin?.length) ? columnSchema.checks.isin : config.editorParams.values;
        if (config.editorParams.values) {
          config.hozAlign = "center";
        }
      } else if (columnSchema.dtype.includes("int") || columnSchema.dtype.includes("float")) {
        config.hozAlign = "right";
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
    toggleGroupRefColumns() {
      this.groupByRefColumns = !this.groupByRefColumns;
      this.table.setGroupBy(this.groupByRefColumns ? this.refColumns : null);
      this.table.setColumns(this.columnsConfig);
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
          (tableRow) => tableRow.getData().reference == row._row.data.reference
        );
      if (selectedRow === undefined) return;

      // Only highlight if the row is not already selected
      if (this.table.getSelectedRows().indexOf(selectedRow) != -1) return;
      this.table.scrollToRow(selectedRow, null, false);
      this.table.deselectRow("visible");
      this.table.toggleSelectRow(selectedRow._row);
    },
    addRow() {
      const selectedRow = this.table.getSelectedRows()?.[0];

      const requiredFields = this.refColumns || [];
      if (this.tableJSON.schema.fields.some((field) => field.name === "reference")) {
        requiredFields.push("reference");
      }
      
      const newRow = {};
      for (const field of this.columns) {
        if (requiredFields.includes(field)) {
          const maxRefValue = getMaxStringValue(field, this.table.getData());
          newRow[field] = incrementReferenceStr(maxRefValue);
        } else {
          newRow[field] = undefined;
        }
      }
      this.table.addRow(newRow, false, selectedRow);
      this.updateTableJsonData();
      this.validateTable();
    },
    dropRow() {
      // Get the selected rows
      const selectedRows = this.table.getSelectedRows();

      // Delete each selected row from the table
      selectedRows.forEach((row) => {
        this.table.deleteRow(row);
      });

      // Update this.tableJSON to reflect the current data in the table
      this.updateTableJsonData();
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
      this.updateTableJsonData();

      this.table.scrollToColumn(newFieldName, null, false);
    },
    columnTitleChanged(column) {
      const newFieldName = column.getDefinition().title.replace(/ /g, "_");
      const oldFieldName = column.getDefinition().field;
      if (!newFieldName || newFieldName == oldFieldName) return;
      if (this.columns.includes(newFieldName)) return;
      console.log("columnTitleChanged:", oldFieldName, newFieldName)

      // Update the field name for all data
      const data = this.table.getData();
      data.forEach((item) => {
        item[newFieldName] = item[oldFieldName];
        del [item, oldFieldName];
      });
      this.table.setData(data);

      this.table.updateColumnDefinition(oldFieldName, {
        field: newFieldName,
        title: newFieldName,
      });

      // Update the field name in the schema
      this.tableJSON.schema.fields = this.tableJSON.schema.fields.map((field) => {
        if (field.name == oldFieldName) {
          return { ...field, name: newFieldName };
        }
        return field;
      });
      this.updateTableJsonData();
      this.validateTable();
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
        console.log(error.stack);
      }
    },
    groupHeader(value, count, data, group) {
      const field = group._group.field
      let header = value
      if (this.referenceValues?.[field]?.hasOwnProperty(value)) {
        const keyValues = Object.entries(this.referenceValues[field][value])
          .filter(([key, value]) => key !== "reference" && value !== 'NA' && value !== null)
          .map(([key, value]) => `${key}: <span style="font-weight:normal; color:black; margin-left:0;">${value}</span>`)
          .join(', ');
        if (keyValues.length > 0) header = keyValues;
      }

      if (count > 1) header = header + `<span style='color:black; margin-left:10px;'>(${count})</span>`;
      return header;
    },
  },
  mounted() {
    if (!this.tableJSON) return;
    const layout = this.columnsConfig.length <= 2 ? "fitDataStretch" : "fitDataTable";
    
    this.table = new Tabulator(this.$refs.table, {
      maxHeight: "50vh",
      data: this.tableJSON.data,
      persistence: { columns: true },
      layoutColumnsOnNewData: true,
      reactiveData: true,
      clipboard: true,
      columnDefaults: {
        resizable: true,
        headerWordWrap: true,
        headerSort: false,
        tooltip: this.cellTooltip.bind(this),
        headerTooltip: this.headerTooltip.bind(this),
      },
      columns: this.columnsConfig,
      index: this.columnsConfig.find((column) => column.field === "reference")
        ? "reference"
        : null,
      groupBy: this.groupByRefColumns ? this.refColumns: null,
      groupToggleElement: "header",
      groupHeader: this.groupHeader,
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
      this.isLoaded = true;
      this.table.setColumns(this.columnsConfig);
      this.validateTable();
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
  }
}
</style>
