<template>
  <div class="table-container">
    <div class="--table-buttons">
      <BaseButton v-show="refColumns?.length || columns.includes('reference')" @click.prevent="toggleShowRefColumns">
        <span v-if="!showRefColumns">Show references</span>
        <span v-else>Hide references</span>
      </BaseButton>
    </div>

    <div ref="table" class="--table" />

    <div class="--table-buttons">
      <BaseDropdown v-show="editable" :visible="visibleEditDropdown">
        <span slot="dropdown-header">
          <BaseButton @click.prevent="visibleEditDropdown=!visibleEditDropdown">
            Edit table
            <svgicon name="chevron-down" width="8" height="8" />
          </BaseButton>
        </span>
        <span slot="dropdown-content">
          <BaseButton v-show="editable" @click.prevent="table.undo();">
            Undo
          </BaseButton>

          <BaseButton v-show="editable" @click.prevent="table.redo();">
            Redo
          </BaseButton>
        </span>
      </BaseDropdown>

      <BaseDropdown v-show="editable" :visible="visibleColumnDropdown" class="add-columns-dropdown">
        <span slot="dropdown-header">
          <BaseButton @click.prevent="visibleColumnDropdown=!visibleColumnDropdown">
            ➕ Add Column
            <svgicon name="chevron-down" width="8" height="8" />
          </BaseButton>
        </span>
        <span slot="dropdown-content" class="--content">
          <BaseButton
            v-for="column in schemaColumns.filter(col => !columns.includes(col))"
            :key="column"
            @click.prevent="addColumn(null, column); visibleColumnDropdown=false"
          >
            {{ column }}
          </BaseButton>
        </span>
      </BaseDropdown>


      <BaseButton v-show="editable" @click.prevent="addRow()">
        ➕ Add Row
      </BaseButton>

      <BaseDropdown v-show="columnValidators && Object.keys(columnValidators).length"
        :visible="editable && visibleCheckropdown">
        <span slot="dropdown-header">
          <BaseButton
            @click.prevent="validateTable({ showErrors: true, scrollToError: true }); visibleCheckropdown=!visibleCheckropdown">
            Check data
          </BaseButton>
        </span>
        <span slot="dropdown-content">
          <BaseButton @click.prevent="$emit('updateValidValues', true);">
            Ignore errors
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
import {
  getTableDataFromRecords, findMatchingRefValues, incrementReferenceStr, getMaxStringValue, } from './dataUtils';
import { getColumnValidators } from "./validationUtils";
import { 
  columnSchemaToDesc, 
  cellTooltip,
  headerTooltip,
  groupHeader,
} from "./tableUtils"; 

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
      visibleColumnDropdown: false,
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
        this.$emit("onUpdateAnswer", JSON.stringify(json));
      },
    },
    schemaColumns() {
      return (this.tableJSON?.validation?.columns ? Object.keys(this.tableJSON.validation.columns) : [])
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
        const commonConfig = this.generateCommonConfig(column.name);
        const editableConfig = this.generateColumnEditableConfig(column.name);
        return { ...commonConfig, ...editableConfig };
      });
      return configs;
    },
    groupConfigs() {
      if (this.groupbyColumns.length === 0) {
        return {};
      }

      return {
        groupBy: this.groupbyColumns,
        groupToggleElement: "arrow",
        groupHeader: (...args) => groupHeader(...args, this.referenceValues, this.refColumns),
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
      
      const reference = this.tableJSON?.reference;
      if (!reference) return null;
      let recordTables = getTableDataFromRecords((record) => record?.metadata?.reference == reference)
      const refToRowDict = findMatchingRefValues(this.refColumns, recordTables)

      return refToRowDict;
    },
    columnContextMenu() {
      let menu = [
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
          label: "Add row below",
          disabled: !this.editable,
          action: (e, row) => {
            this.addRow(row);
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
      }

      this.tableJSON.data = this.table.getData();
      this.tableJSON = this.tableJSON; // Trigger the setter
    },
    isRefColumn(field) { 
      return field == "reference" || this.refColumns?.includes(field);
    },
    generateCommonConfig(fieldName) {
      const hide = !this.showRefColumns && this.isRefColumn(fieldName);
      const commonConfig = {
        title: fieldName,
        field: fieldName,
        visible: !hide,
        width: this.isRefColumn(fieldName) ? 50 : undefined,
        validator: this.columnValidators.hasOwnProperty(fieldName)
          ? this.columnValidators[fieldName]
          : null,
        formatter: this.isRefColumn(fieldName) ? (cell, formatterParams) => {
          const value = cell.getValue();
          if (!value) return value;
          else {
            return "<span style='font-weight:bold;'>" + value + "</span>";
          }
        } : null,
      };
      return commonConfig;
    },
    generateColumnEditableConfig(fieldName) {
      if (!this.editable) return {};

      // Default editable config for a column
      var config = {
        editorParams: {
          search: true,
          autocomplete: true,
          selectContents: true,
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

      } else if (this.refColumns?.includes(fieldName)) {
        config.editor = "list";

        if (this.referenceValues?.hasOwnProperty(fieldName)) {
          config.editorParams = {
            ...config.editorParams,
            valuesLookup: false,
            values: Object.entries(this.referenceValues[fieldName]).map(([key, value]) => ({
              label: key,
              value: key,
              data: value
            })),
            placeholderEmpty: "Type to search by keyword...",
            itemFormatter: function (label, value, item, element) {
              const keyValues = Object.entries(item.data)
                .filter(([key, v]) => key !== "reference" && v !== 'NA' && v !== null)
                .map(([key, v]) => `<span style="font-weight:normal; color:black; margin-left:0;">${key}:</span> ${v}`)
                .join(', ');
              return `<strong>${label}</strong>: <div>${keyValues}</div>`;
            },
            filterFunc: function (term, label, value, item) {
              if (String(label).startsWith(term) || value == term) {
                return true;
              } else if (term.length >= 3) {
                return JSON.stringify(item.data).toLowerCase().match(term.toLowerCase());              
              }
              return label === term;
            },
            allowEmpty: true,
            listOnEmpty: true,
            freetext: true,
          };
        } else {
          config.editorParams = {
            ...config.editorParams,
            search: true,
            valuesLookup: 'active',
            listOnEmpty: true,
            freetext: true,
          };
        }
      }
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
      this.table?.setColumns(this.columnsConfig);
    },
    columnMoved(column, columns) {
      this.tableJSON.schema.fields.sort((a, b) => {
        const aIndex = columns.findIndex((col) => col.getField() === a.name);
        const bIndex = columns.findIndex((col) => col.getField() === b.name);
        return aIndex - bIndex;
      });
      this.tableJSON = this.tableJSON; // Trigger the setter
    },
    addRow(selectedRow) {
      const requiredFields = this.refColumns || [];
      if (this.tableJSON.schema.fields.some((field) => field.name === "reference")) {
        requiredFields.push("reference");
      }
      
      const newRow = {};
      for (const field of this.columns) {
        if (requiredFields.includes(field) && selectedRow?._row?.data[field]) {
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
    addColumn(selectedColumn, newFieldName = "newColumn") {
      // Assign a unique name to the new column
      let count = 1;
      while (this.columns.includes(newFieldName)) {
        newFieldName = `newColumn${count}`;
        count++;
      }
      
      let selectedColumnField = null;
      if (selectedColumn && selectedColumn?._column?.field) {
        selectedColumnField = selectedColumn?._column?.field;
      }

      this.table.addColumn({
        ...this.generateCommonConfig(newFieldName),
        ...this.generateColumnEditableConfig(newFieldName),
        editableTitle: newFieldName.includes("newColumn"),
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
      // this.table?.setColumns(this.columnsConfig);
    },
  },

  mounted() {
    if (!this.tableJSON?.data?.length || !this.tableJSON?.schema) return;

    try {
      const layout = this.columnsConfig.length <= 2 ? "fitDataStretch" : "fitDataTable";
      Tabulator.extendModule("keybindings", "bindings");
      this.table = new Tabulator(this.$refs.table, {
        data: this.tableJSON.data,
        layout: layout,
        // minHeight: "50px",
        height: this.tableJSON.data.length >= 20 ? "60vh": 'auto',
        // renderHorizontal: "virtual",
        // persistence: { columns: true },
        // layoutColumnsOnNewData: true,
        // reactiveData: true,

        // selectableRows: true,
        movableRows: true,
        rowHeader: { 
          headerSort: false, resizable: false, rowHandle: true, editor: false,
          minWidth: 30, width: 30, headerHozAlign: "center", hozAlign: "center", 
          formatter: "handle",
        },
        rowContextMenu: this.rowContextMenu,

        columns: this.columnsConfig,
        index: this.indexColumns + this.refColumns,
        ...this.groupConfigs,
        movableColumns: true,
        resizableColumnGuide: true,
        columnDefaults: {
          editor: "input",
          headerSort: false,
          resizable: 'header',
          maxInitialWidth: 350,
          tooltip: cellTooltip,
          headerTooltip: (...args) => headerTooltip(...args, this.tableJSON.validation, this.columnValidators),
          headerWordWrap: true,
          headerContextMenu: this.columnContextMenu,
          editorEmptyValue: "NA",
        },

        //enable range selection
        selectableRange: 1,
        selectableRangeColumns: true,
        selectableRangeRows: true,
        selectableRangeClearCells: true,
        editTriggerEvent: this.editable ? "dblclick" : false,

        //configure clipboard to allow copy and paste of range format data
        clipboard: true,
        clipboardCopyStyled: false,
        clipboardCopyConfig: {
          rowHeaders: false,
          columnHeaders: false,
        },
        clipboardCopyRowRange: "range",
        clipboardPasteParser: this.editable ? "range" : null,
        clipboardPasteAction: this.editable ? "range" : null,

        validationMode: "highlight",
        history: this.editable,
      });

      if (this.editable) {
        this.table.on("columnTitleChanged", this.columnTitleChanged.bind(this));
        this.table.on("columnMoved", this.columnMoved.bind(this));
      }

      this.table.on("tableBuilt", () => {
        this.isLoaded = true;
        this.table?.setColumns(this.columnsConfig);
        this.validateTable();
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
};
</script>

<style lang="scss">
.table-container {
  display: flex;
  flex-flow: column;
  position: relative;
  max-width: 100%;
  margin-bottom: 0;
  height: 100%;

  .--table {
    overflow: auto;
    white-space: normal;
    resize: vertical;
    overflow: auto;
    position: relative;
    height: auto;
  }
  
  .--table-buttons {
    display: flex;
    justify-content: space-between;
    padding: 5px 5px 0 0;
    margin-bottom: 0;
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

  .add-columns-dropdown {
    position: relative;
    z-index: 1; 

    .__content {
      max-height: 100px; 
      overflow-y: auto; 
    }
  }
}
// .tabulator .tabulator-header .tabulator-col .tabulator-col-content .tabulator-col-title {
//   white-space: normal;
// }

.tabulator .tabulator-group {
  display: grid;
  grid-auto-flow: column;
  justify-content: start;
  // padding-top: 3px;
  // padding-bottom: 3px;
  // border: none;
  background-color: transparent;

  span, small {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    text-decoration: none;
  }

  @media (hover:hover) and (pointer:fine) {
    &:hover {
      cursor: auto;
    }
  }

  &.tabulator-group-visible {
    .tabulator-arrow {
      width: 10px;
      
      &:before {
        content: "";
        position: absolute;
        top: -20px;
        bottom: -20px;
        left: -20px;
        right: -20px;
      }

      &:hover {
        cursor: pointer;
        border-top: 6px solid black;
      }
    }
  }

  .tabulator-arrow {
    position: relative;

    &:before {
      content: "";
      position: absolute;
      top: -20px;
      bottom: -20px;
      left: -20px;
      right: -20px;
    }

    &:hover {
      cursor: pointer;
    }
  }

  &.tabulator-group-level-2,
  &.tabulator-group-level-3,
  &.tabulator-group-level-4,
  &.tabulator-group-level-5 {
    border: none;
  }
}

</style>
