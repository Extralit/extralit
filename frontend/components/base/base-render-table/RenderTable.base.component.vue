<template>
  <div class="table-container">
    <div class="--table-buttons">
      <BaseButton v-show="refColumns?.length || columns.includes('reference')" @click.prevent="toggleShowRefColumns">
        <span v-if="!showRefColumns">⬇️ Show reference columns</span>
        <span v-else>⬅️ Hide reference columns</span>
      </BaseButton>
    </div>

    <div ref="table" class="--table" />

    <div class="--table-buttons">
      <BaseDropdown 
        v-show="editable"
        :visible="visibleEditDropdown">
        <span slot="dropdown-header">
          <BaseButton @click.prevent="visibleEditDropdown=!visibleEditDropdown">
            Edit table 
            <svgicon name="chevron-down" width="8" height="8" />
          </BaseButton>
        </span>
        <span slot="dropdown-content">
          <BaseButton v-show="editable" @click.prevent="table.undo();">
            ↩️ Undo
          </BaseButton>

          <BaseButton v-show="editable" @click.prevent="table.redo();">
            ↪️ Redo
          </BaseButton>

          <BaseButton @click.prevent="addColumn">
            ➕ Add Column
          </BaseButton>

          <BaseButton @click.prevent="addRow">
            ➕ Add Row
          </BaseButton>
        </span>
      </BaseDropdown>

      <BaseDropdown 
        v-show="editable && columns && columnValidators && Object.keys(columnValidators).length"
        :visible="visibleCheckropdown">
        <span slot="dropdown-header">
          <BaseButton @click.prevent="validateTable({ showErrors: true, scrollToError: true }); visibleCheckropdown=!visibleCheckropdown">
            ✅ Check data
          </BaseButton>
        </span>
        <span slot="dropdown-content">
          <BaseButton @click.prevent="$emit('updateValidValues', true);">
            ⏭️ Ignore errors
          </BaseButton>
        </span>
      </BaseDropdown>
    </div>
  </div>
</template>

<script>
import { Notification } from "@/models/Notifications";
import { TabulatorFull as Tabulator } from "tabulator-tables";
import "tabulator-tables/dist/css/tabulator.min.css";
import { getColumnValidators } from "./validationUtils";
import { 
  columnSchemaToDesc, 
  getTableDataFromRecords as getTablesFromRecords, 
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
      showRefColumns: false,
      isLoaded: false,
      visibleCheckropdown: false,
      visibleEditDropdown: false,
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
        const ref_columns = this.tableJSON.schema.fields
          .map(field => field.name)
          .filter(name => typeof name === 'string' && name.endsWith('_ref'));
          
        return ref_columns;
      } catch (error) {
        console.error("Failed to get refColumns:", error);
        return [];
      }
    },
    groupbyColumns() {
      return this.refColumns?.filter((column) => column != 'publication_ref');
    },
    columns() {
      return this.table?.getColumns()?.map((col) => col.getField()) || [];
    },
    columnValidators() { 
      return getColumnValidators(this.tableJSON);
    },
    columnsConfig() {
      if (!this.tableJSON?.schema) return [];

      const configs = this.tableJSON.schema.fields.map((column) => {
        const hide = !this.showRefColumns && this.isRefColumn(column.name) || column.name == 'publication_ref';

        return {
          title: column.name,
          field: column.name,
          visible: !hide,
          validator: this.columnValidators.hasOwnProperty(column.name)
            ? this.columnValidators[column.name]
            : null,
          formatter: this.isRefColumn(column.name) ? (cell, formatterParams) => {
            const value = cell.getValue();
            if (!value) return value;
            else {
              return "<span style='font-weight:bold;'>" + value + "</span>";
            }
          } : null,
          ...this.getColumnEditableConfig(column.name),
        }
      });
      if (this.editable) {
        configs.unshift({ 
          rowHandle: true, 
          formatter: "rowSelection", 
          headerSort: false, frozen: false, hozAlign: "center", width: 30, minWidth: 30,
        });
        // configs.push({ formatter: "buttonCross", width: 30, hozAlign: "center" })
      }
      return configs;
    },
    groupConfigs() {
      if (this.groupbyColumns.length === 0) {
        return {};
      }

      return {
        groupBy: this.groupbyColumns,
        groupToggleElement: "arrow",
        groupHeader: this.groupHeader,
        groupUpdateOnCellEdit: true,
        groupContextMenu: [
          {
            label: "Show reference",
            action: (e, group) => {
              group.popup(`${group._group.field}: ${group._group.key}`, "right");
            }
          },
          {
            separator: true,
          },
          {
            label: "Delete group of rows",
            disabled: !this.editable,
            action: (e, group) => {
              group._group.rows.forEach((row) => {
                row.delete();
              });
              this.updateTableJsonData(true);
            }
          },
        ],
      };
    },
    referenceValues() {
      // First get the metadata.reference from the current table by checking the first row's _ref columns, 
      // then use refValues to find the matching tables from other records and get the dict of reference values to rows
      if (!this.refColumns) return null;
      const firstRow = this.tableJSON?.data?.find((row) => 
        this.refColumns.some((refColumn) => row[refColumn] !== undefined)
      )
      if (!firstRow) return null;
      
      const refValues = this.refColumns.reduce((acc, refColumn, index) => {
        acc[refColumn] = firstRow[refColumn];
        return acc;
      }, {});
      if (!refValues) return null;
  
      const publication_ref = firstRow.publication_ref || firstRow[this.refColumns[0]]?.split('-')[0];
      if (!publication_ref) return null;
      let recordTables = getTablesFromRecords((record) => record?.metadata?.reference == publication_ref, publication_ref)
      const refToRowDict = findMatchingRefValues(refValues, recordTables)

      return refToRowDict;
    },
    columnContextMenu() {
      let menu = [
        {
          label: "Copy column data",
          action: (e, column) => {
            let title = column.getDefinition().title
            let values = column.getCells().map((cell) => cell.getValue());

            navigator.clipboard.writeText([title, ...values].join("\n"));
          }
        },
        {
          separator: true,
        },
        {
          label: "Add column",
          disabled: !this.editable,
          action: (e, column) => {
            this.addColumn(column);
          }
        },
        {
          label: "Rename column",
          disabled: !this.editable,
          action: (e, column) => {
            if (column.getDefinition().frozen) return;
            column.updateDefinition({
              editableTitle: !column.getDefinition().editableTitle,
            });
          }
        },
        {
          label: "Delete column",
          disabled: !this.editable,
          action: (e, column) => {
            column.delete();
            this.updateTableJsonData(true);
          }
        },
      ];
      return menu;
    },
    rowContextMenu() {
      let menu = [
        {
          label: "Copy row",
          action: (e, row) => {
            let rowData = row.getData();
            let values = this.columns.map((column) => rowData[column]);
            navigator.clipboard.writeText(values.join("\t"));
          }
        },
        {
          label: "Paste",
          disabled: !this.editable,
          action: (e, row) => {
            navigator.clipboard.readText().then((text) => {
              const values = text.trim().split("\t");
              const currentRow = row.getData();

              Object.keys(currentRow)
                .filter(columnName => this.isRefColumn(columnName) || this.columns.includes(columnName))
                .forEach((columnName, index) => {
                  if (values[index] === undefined) return;
                  currentRow[columnName] = values[index];
                });
              row.update(currentRow);
              this.updateTableJsonData();
            });
          }
        },
        {
          separator: true,
        },
        {
          label: "Add row below",
          disabled: !this.editable,
          action: (e, row) => {
            this.selectRow(row);
            this.addRow();
          }
        },
        {
          label: "Delete row",
          disabled: !this.editable,
          action: (e, row) => {
            row.delete();
            this.updateTableJsonData(true)
          }
        },
      ];
      return menu;
    }
  },

  methods: {
    updateTableJsonData(remove = false, add = false, update = false, newFieldName=null, oldFieldName=null) {
      if (remove) {
        const removeColumns = this.tableJSON.schema.fields
          .filter((field) => !this.columns.includes(field.name))
          .map((field) => field.name);
          
        if (removeColumns.length > 0) {
          console.log('removeColumns', removeColumns)
          // Remove removeColumns from this.tableJSON.schema
          this.tableJSON.schema.fields = this.tableJSON.schema.fields.filter(
            (field) => !removeColumns.includes(field.name)
          );

          // Remove removeColumns from this.tableJSON.data
          this.tableJSON.data.forEach((row) => {
            removeColumns.forEach((column) => {
              delete row[column];
            });
          });
        }
      }

      if (add) {
        const addColumns = this.columns.filter(
          (field) => !this.tableJSON.schema.fields.map((field) => field.name).includes(field) && field != undefined);

        // Add the new field to the schema
        const data = this.table.getData()
        data.forEach((item) => {
          addColumns.forEach((column) => {
            item[column] = null;
          });
        });

        this.table.setData(data);
        addColumns.forEach((column) => {
          this.tableJSON.schema.fields.push({
            name: column,
            type: "string",
          });
        });
      }

      if (update) {
        // Update the field name for all data
        const data = this.table.getData()
        data.forEach((row) => {
          row[newFieldName] = row[oldFieldName];
          delete row[oldFieldName];
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

        console.log("update:", 'data', data, 'tableJSON.schema.fields', this.tableJSON.schema.fields, 'currentColumns', this.columns);
      }

      this.tableJSON.data = this.table.getData();
      this.tableJSON = this.tableJSON; // Trigger the setter
    },
    isRefColumn(field) { 
      return field == "reference" || this.refColumns?.includes(field);
    },
    getColumnEditableConfig(fieldName) {
      if (!this.editable) return {};

      // Default editable config for a column
      var config = {
        editor: "input",
        editorParams: {
          selectContents: true,
          search: true,
          autocomplete: true,
        },
        headerDblClick: (e, column) => {
          // Enable editable title on double click
          if (!column.getDefinition().frozen && !column.getDefinition().editableTitle) {
            column.updateDefinition({ editableTitle: true });
          }
        },
        headerMenu: (e, column) => {
          if (column.getDefinition().editableTitle) {
            return [{
              label: "Accept",
              action: (e, column) => {
                if (column.getDefinition().frozen) return;
                column.updateDefinition({
                  editableTitle: !column.getDefinition().editableTitle,
                });
              }
            }];
          }
          return this.columnContextMenu;
        },
        cellEdited: (cell) => {
          this.updateTableJsonData();
          this.validateTable();
        },
      };

      if (this.tableJSON.validation?.columns?.hasOwnProperty(fieldName)) {
        // Add custom editor params for a column based on the Pandera validation schema
        const columnSchema = this.tableJSON.validation?.columns[fieldName];

        if (columnSchema.dtype === "str") {
          config.editor = "autocomplete";
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

      } else if (this.refColumns?.includes(fieldName)) {
        config.editor = "autocomplete";

        if (this.referenceValues?.hasOwnProperty(fieldName)) {
          config.editorParams = {
            search: true,
            values: this.referenceValues[fieldName],
            itemFormatter: (label, value, item, element) => {
              const keyValues = Object.entries(label)
                .filter(([key, value]) => key !== "reference" && value !== 'NA' && value !== null)
                .map(([key, value]) => `<span style="font-weight:normal; color:black; margin-left:0;">${key}:</span> ${value}`)
                .join(', ');
              return "<strong>" + value + "</strong>: <div>" + keyValues + "</div>";
            },
            showListOnEmpty: true,
            freetext: true,
          };
        } else {
          config.editorParams = {
            search: true,
            valuesLookup: 'active',
            showListOnEmpty: true,
            freetext: true,
          };
        }
      }

    //   config.editorParams.filterFunc = (term, label, value, item) => {
    //     //term - the string value from the input element
    //     //label - the text lable for the item
    //     //value - the value for the item
    //     //item - the original value object for the item
    //     if (value == "NA") return false;

    //     return term === value;
    // }

      return config;
    },
    validateTable(options) {
      var validErrors = this.table.validate();
      const isValid = validErrors === true;
      this.$emit("updateValidValues", isValid);
      if (isValid) return true;

      if (options?.scrollToError == true) {
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
    toggleShowRefColumns() {
      this.showRefColumns = !this.showRefColumns;
      // this.table.setGroupBy(this.showRefColumns ? this.groupbyColumns : null);
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
      let selectedRow = row;
      // if (this.columns.includes("reference")) {
      //   // Highlight all rows with the same index accross different tables
      //   selectedRow = this.table
      //     .getRows()
      //     .find(
      //       (tableRow) => tableRow.getData().reference == row._row.data.reference
      //     );
      // } else {
      //   selectedRow = this.table.getRows().find((tableRow) => tableRow._row.data == row._row.data);
      // }
      
      // // Only highlight if the row is not already selected
      // if (selectedRow === undefined) return;
      // if (this.table.getSelectedRows().indexOf(selectedRow) != -1) return;
      
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
        if (requiredFields.includes(field) && selectedRow._row.data[field]) {
          newRow[field] = selectedRow._row.data[field]
          // const maxRefValue = getMaxStringValue(field, this.table.getData());
          // newRow[field] = incrementReferenceStr(maxRefValue);
        } else {
          newRow[field] = undefined;
        }
      }
      this.table.addRow(newRow, false, selectedRow);
      this.updateTableJsonData();
      this.validateTable();
      if (!this.showRefColumns) this.toggleShowRefColumns();
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
    addColumn(selectedColumn) {
      let newFieldName = "newColumn";
      // Assign a unique name to the new column
      let count = 1;
      while (this.columns.includes(newFieldName)) {
        newFieldName = `newColumn${count}`;
        count++;
      }

      let selectedColumnField = null;
      if (selectedColumn && selectedColumn.hasOwnProperty('getDefinition')) {
        let selectedColumnField = selectedColumn?.getDefinition()?.field;
        console.log("selectedColumnField:", selectedColumnField)
      }

      this.table.addColumn({
        title: newFieldName,
        field: newFieldName,
        editableTitle: true,
        ...this.getColumnEditableConfig(newFieldName),
      }, false, selectedColumnField)

      this.updateTableJsonData(false, true);
      this.table.scrollToColumn(newFieldName, null, false);
    },
    columnTitleChanged(column) {
      const newFieldName = column.getDefinition().title.replace('.', ' ');
      const oldFieldName = column.getDefinition().field;
      if (!newFieldName?.length || newFieldName == oldFieldName) return;
      if (this.columns.includes(newFieldName)) {
        setTimeout(() => {
          const message = `Column name '${newFieldName}' already exists. Please choose a different name.`;
          Notification.dispatch("notify", {
            message: message,
            numberOfChars: message.length,
            type: "warning",
            onClick() {
              Notification.dispatch("clear");
            },
          });
        }, 500);
        return;
      }
      console.log("columnTitleChanged:", oldFieldName, newFieldName)

      if (column.getDefinition().editableTitle) {
        column.updateDefinition({
          editableTitle: false
        });
      }

      this.updateTableJsonData(false, false, true, newFieldName, oldFieldName);
      // this.table.setColumns(this.columnsConfig);
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
          .filter(([key, value]) => key !== "reference" && !this.refColumns?.includes(key) && value !== 'NA' && value)
          .map(([key, value]) => `<span style="font-weight:normal; color:black; margin-left:0;">${key}:</span> ${value}`)
          .join(', ');

        if (keyValues.length > 0) {
          header = `<small style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" text="${value}">${keyValues}</small>`
        }
      }

      if (count > 1) header = header + `<span style='color:black; margin-left:10px;'>(${count})</span>`;
      return header;
    },
  },

  mounted() {
    if (!this.tableJSON?.data?.length || !this.tableJSON?.schema) return;

    try {
      const layout = this.columnsConfig.length <= 2 ? "fitDataStretch" : "fitDataTable";
      
      this.table = new Tabulator(this.$refs.table, {
        data: this.tableJSON.data,
        layout: layout,
        minHeight: "200px",
        maxHeight: "50vh",
        // renderHorizontal: "virtual",
        // persistence: { columns: true },
        // layoutColumnsOnNewData: true,
        reactiveData: true,
        clipboard: true,
        columnDefaults: {
          resizable: true,
          headerSort: false,
          tooltip: this.cellTooltip.bind(this),
          headerTooltip: this.headerTooltip.bind(this),
          headerWordWrap: true,
          headerContextMenu: this.columnContextMenu,
          // maxWidth: 200,
        },
        columns: this.columnsConfig,
        index: this.columnsConfig.find((column) => column.field === "reference")
        ? "reference"
        : null,
        ...this.groupConfigs,
        // selectable: 1,
        // selectablePersistence: true,
        validationMode: "highlight",
        movableRows: this.editable,
        movableColumns: this.editable,
        rowContextMenu: this.rowContextMenu,
        history: true,
      });

      // this.table.on("rowClick", this.clickRow.bind(this));

      if (this.editable) {
        this.table.on("columnTitleChanged", this.columnTitleChanged.bind(this));
        this.table.on("columnMoved", this.columnMoved.bind(this));
      }

      this.table.on("tableBuilt", () => {
        this.isLoaded = true;
        this.table.setColumns(this.columnsConfig);
        this.validateTable();

        // this.$nuxt.$on("on-table-highlight-row", this.selectRow.bind(this));
      }); 

    } catch (error) {
      const message = `Failed to load table: ${error}`;
      Notification.dispatch("notify", {
        message: message,
        numberOfChars: message.length,
        type: "error",
        onClick() {
          Notification.dispatch("clear");
        },
      });
      console.error("Failed to mount table:", error);
    }
  },

  beforeDestroy() {
    this.$nuxt.$off("on-table-highlight-row");
  },
};
</script>

<style lang="scss">
.table-container {
  display: flex;
  flex-flow: column;
  position: relative;
  max-width: 100%;
  // overflow-x: auto;
  // background: inherit;

  .--table-buttons {
    display: flex;
    justify-content: space-between;
    padding: 5px 5px 10px 0;
    color: white;
    border-radius: 5px;
    text-decoration: none;

    .button {
      cursor: pointer;
      &:hover,
      &--active {
        background: $black-4;
      }
    }
  }

  .--table {
    overflow: auto;
    white-space: normal;
  }
}
// .tabulator .tabulator-header .tabulator-col .tabulator-col-content .tabulator-col-title {
//   white-space: normal;
// }

.tabulator .tabulator-group-level-1 {
  max-height: 100px;
}

.tabulator .tabulator-group .tabulator-group-value {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

</style>
