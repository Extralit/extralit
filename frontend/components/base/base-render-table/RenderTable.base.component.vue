<template>
  <div class="table-container">
    <div ref="table" class="--table"/>
    
    <div class="--buttons">
      <button v-show="indexColumns?.length" @click="toggleColumnFreeze">⬅️ Toggle column freeze</button>
      <button @click="validateTable">✅ Validate</button>
      <button v-show="editable" @click="addColumn">➕ Add column</button>
      <button v-show="editable" @click="addRow">➕ Add row</button>
    </div>
  </div>
</template>

<script>
import { TabulatorFull as Tabulator, MoveColumnsModule } from 'tabulator-tables';
import "tabulator-tables/dist/css/tabulator.min.css";

export default {
  name: 'RenderTableBaseComponent',
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
    }
  },
  model: {
    prop: 'hasValidValues',
    event: 'updateValidation'
  },
  data() {
    return {
      table: null,
      indexColumns: [],
      numRows: 0,
      freezeColumns: true,
    };
  },
  computed: {
    tableJSON: {
      get() {
        try {
          const json = JSON.parse(this.tableData)
          this.numRows = json.data.length;
          this.indexColumns = json.schema.primaryKey;

          return json;

        } catch (error) {
          console.error("Failed to parse JSON:", error);
          return null;
        }
      },
      set(json) {
        this.$nuxt.$emit('on-update-response-tabledata', JSON.stringify(json));
      }
    },
    columns() {
      return this.table?.getColumns().map(col => col.getField())
    },
    editableColumnsConfig() {
      if (this.editable) {
        return {
          editor: "input",
          editorParams: {
            selectContents: true,
          },
          editableTitle: false,
          headerDblClick: function (e, column) {
            // Enable editable title on double click
            column.updateDefinition({ editableTitle: !column.getDefinition().editableTitle });
          },
          cellEdited: (cell) => {
            this.tableJSON.data = this.table.getData();
            this.validateTable();
            this.tableJSON = this.tableJSON  // Trigger the setter
          },
        };
      }
      return {};
    },
    columnsConfig() {
      if (!this.tableJSON?.schema) return [];

      let configs = this.tableJSON.schema.fields.map((column, index) => ({
        title: column.name === 'index' && index === 0 ? '' : column.name,
        field: column.name,
        frozen: this.freezeColumns && this.indexColumns?.length && this.indexColumns.includes(column.name),
        // formatter: "textarea",
        ...this.editableColumnsConfig,
        validator: this.columnValidators.hasOwnProperty(column.name) ? this.columnValidators[column.name] : null,
      }));
      // columns.unshift({ rowHandle: true, formatter: "handle", headerSort: false, frozen: true, width: 30, minWidth: 30 },);
      
      return configs
    },
    columnValidators() {
      const tabulatorValidators = {};
      const tableColumns = this.tableJSON.schema.fields.map(col => col.name);
      const panderaColumns = this.tableJSON.validation?.columns;

      if (!panderaColumns) return tabulatorValidators;

      for (const [columnName, columnSchema] of Object.entries(panderaColumns)) {
        if (!tableColumns.includes(columnName)) continue;

        const validators = [];

        if (columnSchema.required) {
          validators.push("required");
        }

        switch (columnSchema.dtype) {
          case "str":
            validators.push("string");
            break;
          case "int64":
            validators.push("integer");
            break;
          case "float64":
            validators.push("float");
            break;
          default:
            break;
        }

        if (columnSchema.checks) {
          if (columnSchema.checks.greater_than_or_equal_to !== undefined) {
            validators.push(`min:${columnSchema.checks.greater_than_or_equal_to}`);
          }

          if (columnSchema.checks.isin) {
            validators.push(`in:${columnSchema.checks.isin.join("|")}`);
          }
        }

        // Custom validator example for unique check
        if (columnSchema.unique) {
          const uniqueValidator = {
            type: function (cell, value, parameters) {
              const columnValues = cell.getTable().getData().map(row => row[cell.getField()]);
              return columnValues.filter(v => v === value).length === 1;
            },
          };
          validators.push(uniqueValidator);
        }
        tabulatorValidators[columnName] = validators;
      }

      return tabulatorValidators;
    }
  },
  methods: {
    toggleColumnFreeze() {
      this.freezeColumns = !this.freezeColumns;
      this.table.setColumns(this.columnsConfig);
    },
    clickRow(e, row) {
      row.toggleSelect();
      this.$nuxt.$emit('on-table-highlight-row', row);
    },
    selectRow(row) {
      // Highlight all rows with the same index accross different tables
      const rowColumns = Object.keys(row?._row.data);
      // Ensures only to highlight on tables with the same columns
      if (rowColumns.length !== this.columns.length || !rowColumns.every(val => this.columns.includes(val))) return;

      // const selectedRow = this.table.getRows()[pos - 1]
      const selectedRow = this.table.getRows().find(tableRow => JSON.stringify(tableRow.getData()) === JSON.stringify(row._row.data));
      if (selectedRow === undefined) return;

      // Only highlight if the row is not already selected
      if (this.table.getSelectedRows().indexOf(selectedRow) != -1) return;
      this.table.scrollToRow(selectedRow, null, false);
      this.table.deselectRow("visible");
      this.table.toggleSelectRow(selectedRow._row)
    },
    addRow() {
      const selectedRows = this.table.getSelectedRows();
      if (selectedRows.length > 0) {
        const selectedRow = selectedRows[0];
        this.table.addRow({}, false, selectedRow);
      } else {
        this.table.addRow({}).then((row) => { row.validate() });
      }
    },
    addColumn() {
      const newFieldName = "newColumn";

      this.table.addColumn({
        title: newFieldName,
        field: newFieldName,
        ...this.editableColumnsConfig
      }, false);

      // Add the new field to the schema
      const data = this.table.getData();
      data.forEach(item => {
        item[newFieldName] = '';
      });
      this.table.setData(data);
      this.tableJSON.schema.fields.push({
        name: newFieldName,
      });
      this.tableJSON = this.tableJSON  // Trigger the setter

      this.table.scrollToColumn(newFieldName, "middle", false);
    },
    columnTitleChanged(column) {
      const newFieldName = column.getDefinition().title.replace(/ /g, '_');
      const oldFieldName = column.getDefinition().field

      // Update the field name for all data
      const data = this.table.getData();
      data.forEach(item => {
        item[newFieldName] = item[oldFieldName];
        delete item[oldFieldName];
      });

      // Update the table data
      this.table.setData(data);
      this.tableJSON.data = data;

      this.table.updateColumnDefinition(column.getField(), {
        field: newFieldName
      });

      // Update the field name in the schema
      this.tableJSON.schema.fields = this.tableJSON.schema.fields.map(field => {
        if (field.name === oldFieldName) {
          return { ...field, name: newFieldName };
        }
        return field;
      });
      this.tableJSON = this.tableJSON  // Trigger the setter

      this.table.scrollToColumn(newFieldName, "middle", false);
    },
    cellTooltip: function (e, cell, onRendered) {
      var text = cell.getValue();

      if (text?.length > 100) {
        return text;

      } else if (cell?._cell?.column.field === 'index' && this.tableJSON?.validation.columns.hasOwnProperty(text)) {
        const column_schema = this.tableJSON.validation.columns[text]
        return column_schema.description
      } 
      return null;
    },
    headerTooltip(e, column, onRendered) {
      const fieldName = column.getDefinition().field;
      
      let desc = this.tableJSON.schema.fields.find(col => col.name === fieldName)?.description;

      if (this.tableJSON?.validation?.columns.hasOwnProperty(fieldName)) {
        const panderaSchema = this.tableJSON?.validation.columns[fieldName];
        desc = `${panderaSchema.description}`;
        if (this.columnValidators.hasOwnProperty(fieldName)) {
          desc += `<br/><br/>Checks: ${this.columnValidators[fieldName]}`.replace(/,/g, ', ').replace(/:/g, ': ');
        }
      }

      if (!desc) return null;
      return desc;
    },
    validateTable() {
      var valid = this.table.validate();
      this.$emit('updateValidation', valid === true);
    }
  },
  mounted() {
    const layout = this.columnsConfig.length <= 2 ? "fitDataStretch" : "fitDataTable"

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
        maxWidth: layout === 'fitDataTable' ? 150 : null,
        headerWordWrap: true,
        headerSort: false,
        tooltip: this.cellTooltip,
        headerTooltip: this.headerTooltip,
      },
      columns: this.columnsConfig,
      layout: layout,
      selectable: 1,
      selectablePersistence: true,
      validationMode: "highlight",
      movableColumns: this.editable,
    });

    this.table.on('columnTitleChanged', this.columnTitleChanged);
    this.table.on('rowClick', this.clickRow);
    this.$nuxt.$on('on-table-highlight-row', this.selectRow);
    this.table.on('columnMoved', (column, columns) => {
      this.tableJSON.schema.fields.sort((a, b) => {
        const aIndex = columns.findIndex(col => col.getField() === a.name);
        const bIndex = columns.findIndex(col => col.getField() === b.name);
        return aIndex - bIndex;
      });
      this.tableJSON = this.tableJSON  // Trigger the setter
    });
    this.table.on('tableBuilt', () => {
      this.validateTable();
    });
    
  },
  beforeDestroy() {
    this.$nuxt.$off('on-table-highlight-row');
  }
}
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