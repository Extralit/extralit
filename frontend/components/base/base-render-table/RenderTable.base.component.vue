<template>
  <div class="table-container">
    <div ref="table" class="--table"/>
    
    <div class="--buttons">
      <button v-if="indexColumns?.length" @click="toggleColumnFreeze">⬅️ Toggle column freeze</button>
      <button v-if="editable" @click="addColumn">➕ Add column</button>
      <button v-if="editable" @click="addRow">➕ Add row</button>
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
      }));


      // columns.unshift({ rowHandle: true, formatter: "handle", headerSort: false, frozen: true, width: 30, minWidth: 30 },);
      
      return configs
    },
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
      this.table.scrollToRow(selectedRow, "center", false);
      this.table.deselectRow("visible");
      this.table.toggleSelectRow(selectedRow._row)
    },
    addRow() {
      const selectedRows = this.table.getSelectedRows();
      if (selectedRows.length > 0) {
        const selectedRow = selectedRows[0];
        this.table.addRow({}, false, selectedRow);
      } else {
        this.table.addRow({});
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
      const desc = this.tableJSON.schema.fields.find(col => col.name === fieldName)?.description;

      if (!desc) return null;
      return desc;
    },
    convertPanderaToTabulator(validation) {
      const tabulatorColumns = [];

      for (const [columnName, columnSchema] of Object.entries(validation.columns)) {
        const tabulatorColumn = {
          title: columnSchema.title || columnName,
          field: columnName,
          description: columnSchema.description || "",
          validator: [],
        };

        if (!columnSchema.nullable) {
          tabulatorColumn.validator.push("required");
        }

        switch (columnSchema.dtype) {
          case "str":
            tabulatorColumn.validator.push("string");
            break;
          case "int64":
            tabulatorColumn.validator.push("integer");
            break;
          case "float64":
            tabulatorColumn.validator.push("float");
            break;
          default:
            break;
        }

        if (columnSchema.checks) {
          if (columnSchema.checks.greater_than_or_equal_to !== undefined) {
            tabulatorColumn.validator.push(`min:${columnSchema.checks.greater_than_or_equal_to}`);
          }

          if (columnSchema.checks.isin) {
            tabulatorColumn.validator.push(`in:${columnSchema.checks.isin.join("|")}`);
          }
        }

        tabulatorColumns.push(tabulatorColumn);
      }

      return tabulatorColumns;
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
      movableColumns: true,
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
    // this.table.on("cellMouseOver", (e, cell) => {
    //   // console.log(cell._cell.row)
    //   return this.clickRow(e, cell._cell.row)
    // },
    // )
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