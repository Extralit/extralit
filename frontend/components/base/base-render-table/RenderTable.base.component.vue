<template>
  <div class="table-container"
    @focusin="setFocus(true)" 
    @focusout="setFocus(false)"
    @keydown.esc.exact="exitEditionMode"
  >
    <div class="__table-buttons">
      <BaseButton v-show="refColumns?.length || columns.includes('reference')" @click.prevent="toggleShowRefColumns">
        <span v-if="!showRefColumns">Show references</span>
        <span v-else>Hide references</span>
      </BaseButton>
    </div>

    <div ref="table" class="__table" />

    <div class="__table-buttons">
      <BaseDropdown v-show="editable" :visible="dropdownEditTableVisible" >
        <span slot="dropdown-header">
          <BaseButton @click.prevent="dropdownEditTableVisible=!dropdownEditTableVisible">
            Edit table
            <svgicon name="chevron-down" width="8" height="8" />
          </BaseButton>
        </span>
        <span slot="dropdown-content">
          <BaseButton v-show="editable && table" @click.prevent="table.undo();">
            Undo
          </BaseButton>
          <BaseButton v-show="editable && table" @click.prevent="table.redo();">
            Redo
          </BaseButton>
          <BaseButton v-show="editable" @click.prevent="clearTable(); dropdownEditTableVisible=false">
            {{ table?.getDataCount() > 0 ? 'Clear data' : 'Delete table' }}
          </BaseButton>
        </span>
      </BaseDropdown>

      <BaseDropdown v-show="editable && table" :visible="visibleColumnDropdown" class="dropdown"  >
        <span slot="dropdown-header">
          <BaseButton @click.prevent="visibleColumnDropdown=!visibleColumnDropdown">
            ➕ Add Column
            <svgicon name="chevron-down" width="8" height="8" />
          </BaseButton>
        </span>
        <span slot="dropdown-content">
          <BaseButton
            v-for="(attrs, field) in remainingSchemaColumns"
            :key="field"
            :title="`${field}: ${attrs?.description}`"
            @click.prevent="addColumn(null, field); visibleColumnDropdown=false"
          >
            {{ field }}
          </BaseButton>
        </span>
      </BaseDropdown>

      <BaseButton v-show="editable && table" @click.prevent="addRow()">
        ➕ Add Row
      </BaseButton>

      <BaseDropdown v-show="table && columnValidators && Object.keys(columnValidators).length"
        :visible="editable && visibleCheckdropdown" >
        <span slot="dropdown-header">
          <BaseButton
            @click.prevent="validateTable({ scrollToError: true, saveData: true }); visibleCheckdropdown=!visibleCheckdropdown">
            Check data <i v-if="tableJSON.schema.is_latest === false">!</i>
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

<script lang="ts">
import { merge } from 'lodash';
import { Notification } from "@/models/Notifications";
import { ColumnComponent, RangeComponent, TabulatorFull as Tabulator } from "tabulator-tables";
import "tabulator-tables/dist/css/tabulator.min.css";
import { generateCombinations, incrementReferenceStr, getMaxValue } from './dataUtils';
import { getColumnValidators, getColumnEditorParams } from "./validationUtils";
import { cellTooltip, headerTooltip, groupHeader, getRangeRowData, getRangeColumns } from "./tableUtils"; 
import { useExtractionTableViewModel } from "./useExtractionTableViewModel";
import { Question } from "@/v1/domain/entities/question/Question";
import { Data, DataFrame } from './types';
import { difference } from '~/v1/domain/entities/record/Record';

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
    questions: {
      type: Array as () => Question[],
      default: () => [],
    },
  },

  model: {
    prop: "hasValidValues",
    event: "updateValidValues",
  },

  data() {
    return {
      table: null,
      showRefColumns: this.editable,
      isLoaded: false,
      visibleCheckdropdown: false,
      dropdownEditTableVisible: false,
      visibleColumnDropdown: false,
      addColumnSearchText: null,
    };
  },

  watch: {
    tableJSON: {
      deep: true,
      handler(newTableJSON: DataFrame, oldTableJSON: DataFrame) {
        if (!this.editable) return;
        if (newTableJSON?.schema?.schemaName && newTableJSON?.validation?.name) {
          this.$emit("change-text", JSON.stringify({...newTableJSON, validation: undefined}));
        } else {
          this.$emit("change-text", JSON.stringify(newTableJSON));
        }
      },
    },
    columnsConfig: {
      deep: true,
      handler(newColumnsConfig, oldColumnsConfig) {
        if (this.isLoaded) {
          console.warn('Changes columns config', difference(newColumnsConfig, oldColumnsConfig));
        }
      },
    },
  },

  created() {
    try {
      this.fetchValidation().then(() => {
        if (this.isLoaded) {
          console.log('Updating columns config');
          this.table?.setColumns(this.columnsConfig);
          this.validateTable();
        }
      });
    } catch (error) {
      Notification.dispatch("notify", {
        message: `${error.response}: ${error.message}`,
        type: "error",
        onClick() {
          Notification.dispatch("clear");
        },
      });
    }
  },

  computed: {
    remainingSchemaColumns() {
      const filteredColumns = Object.fromEntries(
        Object.entries(this?.validation?.columns || {}).filter(([field, attrs]) => !this.columns.includes(field))
      );
      return filteredColumns || {};
    },
    columnValidators() { 
      return getColumnValidators(this.tableJSON, this.validation);
    },
    columns() {
      return this.table?.getColumns()
        ?.map((col) => col.getField())
        ?.filter(field => field && !field.startsWith('_')) || [];
    },
    columnsConfig() {
      if (!this.tableJSON?.schema) return [];

      var configs = this.tableJSON.schema.fields.map((column) => {
        const commonConfig = this.generateCommonConfig(column.name);
        const editableConfig = this.generateColumnEditableConfig(column.name);
        return { ...commonConfig, ...editableConfig };
      });

      if (!this.editable) {
        return configs;
      } 
      
      if (this.columns.includes("_id")) {
        configs = configs.filter((column) => column.field !== "_id");
      }
      var rownum = 0;
      const idColumn = {
        title: "_id",
        field: "_id",
        visible: false,
        mutator: (value, data, type, params, component) => {
          if (type === "edit") {
            return value;
          } else if (value != null) {
            return value;
          }
          const maxRefValue = getMaxValue(component.getField(), this.table.getData());
          if (rownum < maxRefValue) {
            rownum = maxRefValue+1;
          }
          return rownum++;
        },
      };

      return [idColumn, ...configs];
    },
    groupConfigs() {
      if (this.groupbyColumns.length === 0) {
        return {};
      }

      return {
        groupBy: this.groupbyColumns,
        groupToggleElement: "arrow",
        // @ts-ignore
        groupHeader: (...args: any[]) => groupHeader(...args, this.referenceValues, [...this.refColumns, ...this.indexColumns]),
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
            label: "Delete rows group",
            disabled: !this.editable,
            action: (e, group) => {
              this.deleteGroupRows(group);
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
      let recordTables = this.getTableDataFromRecords((record: any) => record?.metadata?.reference == reference)
      const refToRowDict = this.findMatchingRefValues(this.refColumns, recordTables)

      return refToRowDict;
    },
  
  },

  methods: {
    setFocus(isFocus) {
			this.$emit("on-change-focus", isFocus);
		},
    exitEditionMode() {
			this.setFocus(false)
			this.$emit("on-exit-edition-mode");
		},
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
        const data = this.table.getData().map(({ _id, ...rest }) => rest)
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
        const data = this.table.getData().map(({ _id, ...rest }) => rest)
        data.forEach((row) => {
          row[newFieldName] = row[oldFieldName];
          delete row[oldFieldName];
        });
        this.table.setData(data);

        this.table.updateColumnDefinition(oldFieldName, {
          field: newFieldName,
          title: newFieldName,
          ...this.generateCommonConfig(newFieldName),
          ...this.generateColumnEditableConfig(newFieldName),
        });

        // Update the field name in the schema
        this.tableJSON.schema.fields = this.tableJSON.schema.fields.map((field) => {
          if (field.name == oldFieldName) {
            return { ...field, name: newFieldName };
          }
          return field;
        });
      }

      this.tableJSON.data = this.table.getData().map(({ _id, ...rest }) => rest);
    },
    isIndexRefColumn(field) { 
      return this.indexColumns?.includes(field) || this.refColumns?.includes(field);
    },
    generateCommonConfig(fieldName) {
      const hide = !this.showRefColumns && this.isIndexRefColumn(fieldName);
      const commonConfig = {
        title: fieldName,
        field: fieldName,
        visible: !hide,
        width: this.isIndexRefColumn(fieldName) ? 50 : undefined,
        validator: this.columnValidators.hasOwnProperty(fieldName)
          ? this.columnValidators[fieldName]
          : null,
        formatter: this.isIndexRefColumn(fieldName) ? (cell, formatterParams) => {
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
      let config = {
        editorParams: {
          search: true,
          autocomplete: true,
          selectContents: true,
        },
        headerDblClick: function(e, column) {
          // Enable editable title on double click
          if (!column.getDefinition().frozen && !column.getDefinition().editableTitle) {
            column.updateDefinition({ editableTitle: true });
          }
        },
        headerMenu: !this.isIndexRefColumn(fieldName) ? function(e, column) {
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
        } : null,
        cellEdited: (cell) => {
          this.updateTableJsonData();
          this.validateTable();
        },
      };

      config = merge({}, config, getColumnEditorParams(fieldName, this.validation, this.refColumns, this.referenceValues));

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

      if (options?.saveData == true) {
        this.updateTableJsonData();
      }

      return isValid;
    },
    toggleShowRefColumns() {
      this.showRefColumns = !this.showRefColumns;
      this.table?.setColumns(this.columnsConfig);
    },
    columnMoved(column, columns) {
      this.tableJSON.schema.fields.sort((a, b) => {
        const aIndex = columns.findIndex((col) => col.getField() === a.name);
        const bIndex = columns.findIndex((col) => col.getField() === b.name);
        return aIndex - bIndex;
      });
    },
    addRow(selectedRow, rowData: Record<string, any>={}) {
      // const requiredFields = this.refColumns || this.indexColumns;
      delete rowData._id;
      
      for (const field of this.columns) {
        if (rowData[field] != undefined) {
          continue
        } else if (this.indexColumns.includes(field) && !this.refColumns.includes(field) && 
            selectedRow?.getData()[field]) {
          const maxRefValue = getMaxValue(field, this.table.getData());
          rowData[field] = incrementReferenceStr(maxRefValue);
        } else if (this.refColumns.includes(field) && selectedRow?.getData()[field]) {
          rowData[field] = selectedRow?.getData()[field];
        } else {
          rowData[field] = undefined;
        }
      }
      this.table.addRow(rowData, false, selectedRow);
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
    deleteGroupRows(group) {
      group?.getRows()?.forEach((row) => {
        row?.delete();
      });

      group?.getSubGroups()?.forEach((subGroup) => {
        this.deleteGroupRows(subGroup);
      });
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
      this.columnMoved(null, this.table.getColumns());
      this.table.scrollToColumn(newFieldName, null, false);
    },
    columnTitleChanged(column) {
      const newFieldName = column.getDefinition().title.replace('.', ' ');
      const oldFieldName = column.getDefinition().field;
      if (!newFieldName?.length || newFieldName == oldFieldName) return;
      if (this.columns.includes(newFieldName)) {
        setTimeout(() => {
          Notification.dispatch("notify", {
            message: `Column name '${newFieldName}' already exists. Please choose a different name.`,
            type: "warning",
            onClick() {
              Notification.dispatch("clear");
            },
          });
        }, 500);
        return;
      }

      if (column.getDefinition().editableTitle) {
        column.updateDefinition({
          editableTitle: false
        });
      }

      this.updateTableJsonData(false, false, true, newFieldName, oldFieldName);
      // this.table?.setColumns(this.columnsConfig);
    },
    clearTable() {
      if (this.table?.getDataCount() == 0) {
        this.tableJSON = undefined;
        return;
      }
      this.table?.clearData()
      this.columns?.forEach((column) => {
        if (!this.refColumns.includes(column)) {
          this.table?.deleteColumn(column);
        }
      });
    },
    addEmptyReferenceRows() {
      const combinations = generateCombinations(this.referenceValues);

      combinations.forEach(refValues => {
        this.addRow(null, refValues);
      });
    },
    async completionRange(range: RangeComponent) {
      const rangeData = getRangeRowData(range)
      const rangeColumns = getRangeColumns(range);
      const selectedRowData: Record<string, any> = Object.values(rangeData).map(({ _id, ...rest }) => rest);

      this.completeExtraction(selectedRowData, rangeColumns, this.referenceValues)
        .then((predictedRowData) => {
          this.updateRangeData(predictedRowData, range);
        })
        .catch((error) => {
          console.log(error)
          Notification.dispatch("notify", {
            message: `${error.response}: ${error.message}`,
            type: "error",
            onClick() {
              Notification.dispatch("clear");
            },
          });
        })
    },

    updateRangeData(updateRowsData: Data, range: RangeComponent) {
      const rangeData = getRangeRowData(range)
      const rangeColumns = getRangeColumns(range);
      const selectedIndices = Object.keys(rangeData);

      selectedIndices.forEach((index: string, i: number) => {
        if (!updateRowsData || !updateRowsData[i]) return;
        const predictedRow = updateRowsData[i]
        
        const dataUpdate: Record<string, any> = Object.keys(predictedRow)
          ?.filter(field => rangeColumns.includes(field))
          ?.reduce((acc, field) => {
            try {
              // @ts-ignore
              const cell = range.getRows()[i].getCell(field)._cell;
              this.table.modules.history.action("cellEdit", cell, {
                oldValue: cell.getValue(),
                newValue: predictedRow[field],
                type: "cellEdit"
              });
            } catch (error) {
              console.log(`Failed to create history entry: ${error.message}`);
            }

            acc[field] = predictedRow[field];
            return acc;
          }, {});

        if (dataUpdate) {
          this.table.updateData([{_id: index, ...dataUpdate}])
            .catch(function(error) {
              throw new Error(`Failed to update data: ${error.message} \n${JSON.stringify({_id: index, ...dataUpdate})}`);
            });
        }
      });
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
          action: function(e, column) {
            if (column.getDefinition().frozen) return;
            column.updateDefinition({
              editableTitle: !column.getDefinition().editableTitle,
            });
          }
        },
        {
          label: "Delete column",
          disabled: !this.editable,
          action: (e, column: ColumnComponent) => {
            column.delete();
            console.log('deleted',column)
            this.updateTableJsonData(true);
          }
        },
      ];
      return menu;
    },
    rowContextMenu() {
      let menu = [
        {
          label: "Hey 🤖, yeet this!",
          disabled: !this.editable,
          action: (e, row) => {
            const range = this.table.getRanges()[0];
            this.completionRange(range)
          },
        },
        {
          separator: true,
        },
        {
          label: "Add row below",
          disabled: !this.editable,
          action: (e, row) => {
            this.addRow(row);
          }
        },
        {
          label: "Duplicate row",
          disabled: !this.editable,
          action: (e, row) => {
            let newRowData = { ...row.getData() };
            this.indexColumns.forEach((field) => {
              newRowData[field] = undefined;
            });
            this.addRow(row, newRowData);
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
    },
  },

  mounted() {
    if (!this.tableJSON?.data?.length || !this.tableJSON?.schema) return;

    try {
      Tabulator.extendModule("keybindings", "bindings", null);

      const layout = this.columns.length <= 2 ? "fitData" : "fitDataTable";
      this.table = new Tabulator(this.$refs.table, {
        data: this.tableJSON.data,
        reactiveData: true,
        layout: layout,
        height: this.tableJSON.data.length >= 10 ? "60vh": 'auto',
        persistence:{
          sort: true,
          filter: true,
          headerFilter: true,
          columns: ["frozen"], 
          group:{
            groupBy: true,
            groupStartOpen: true,
            groupHeader: false,
          },
          page: true,
        },
        // renderHorizontal: "virtual",
        renderVertical:"basic",
        layoutColumnsOnNewData: true,
        autoResize: false,
        placeholder: () => {
          const div = document.createElement('div');
          div.classList.add('tabulator-placeholder-contents');

          const p = document.createElement('p');
          p.textContent = 'No data available';
          div.appendChild(p);
          
          if (this.referenceValues) {
            const button = document.createElement('button');
            button.textContent = 'Generate empty rows for every reference';
            // button.style.display = 'inline';
            button.addEventListener('click', this.addEmptyReferenceRows);
            div.appendChild(button);
          }
          return div;
        },

        // Row
        movableRows: true,
        rowHeader: { 
          headerSort: false, resizable: false, rowHandle: true, editor: false,
          minWidth: 30, width: 30, maxWidth: 30, headerHozAlign: "center", hozAlign: "center", 
          formatter: "handle",
        },
        rowContextMenu: this.rowContextMenu,
        index: "_id",

        // Column
        columns: this.columnsConfig,
        ...this.groupConfigs,
        movableColumns: true,
        columnDefaults: {
          editor: "input",
          headerSort: false,
          resizable: 'header',
          maxInitialWidth: 350,
          tooltip: cellTooltip,
          // @ts-ignore
          headerTooltip: (...args: any[]) => headerTooltip(...args, this.validation, this.columnValidators),
          headerWordWrap: true,
          headerContextMenu: this.columnContextMenu,
          editorEmptyValue: "NA",
        },

        // enable range selection
        selectableRange: 1,
        selectableRangeColumns: true,
        selectableRangeRows: true,
        selectableRangeClearCells: true,
        editTriggerEvent: this.editable ? "dblclick" : false,

        // configure clipboard to allow copy and paste of range format data
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
        this.table.on("clipboardPasted", (clipboard, rowData, rows) => {
          this.updateTableJsonData();
          this.validateTable();
        });
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
    }
  },

  setup(props) {
    return useExtractionTableViewModel(props);
  },

  errorCaptured(err, component, info) {
    this.error = err;
    console.error(`Error caught from ${component}: ${err}`);
    return false; // stops the error from propagating further
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

  .__table {
    white-space: normal;
    position: relative;
    resize: vertical;
    overflow: auto;
  }
  
  .__table-buttons {
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

  .dropdown {
    z-index: 1;

    .dropdown__content {
      max-height: 290px;
      overflow-y: auto;

      .button {
        width: 100%;
      }
    }
  }
}

.tabulator {
  .tabulator-header .tabulator-col .tabulator-col-content .tabulator-col-title {
    white-space: normal;
  }

  .tabulator-row {
    min-height: none;
    
    .tabulator-cell {
      // white-space: normal;
      // overflow: visible;
      // text-overflow: clip;
      // word-break: break-word;
    }
  }
  .tabulator-tableholder .tabulator-placeholder .tabulator-placeholder-contents {
    display: block;
    align-items: center;
    justify-content: flex-start;
    text-align: left;
    margin-right: auto;
    margin-left: 20px;
  }

  .tabulator-group {
    display: grid;
    grid-auto-flow: column;
    justify-content: start;
    background-color: palette(white);
    padding-top: 3px;
    padding-bottom: 3px;
    // border: none;
    // box-shadow: 0 0 0 1px #999;
    $group-header-height: 27px;

    span, small {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      text-decoration: none;
    }

    @media (hover:hover) and (pointer:fine) {
      &:hover {
        cursor: auto;
        background: palette(white);
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

    &.tabulator-group-level-0,
    &.tabulator-group-level-1,
    &.tabulator-group-level-2,
    &.tabulator-group-level-3,
    &.tabulator-group-level-4,
    &.tabulator-group-level-5 {
      position: -webkit-sticky;
      position: sticky;
      z-index: 100;
    }

    &.tabulator-group-level-0 {
      top: 0;
    }
    &.tabulator-group-level-1 {
      top: calc(1 * #{$group-header-height});
    }
    &.tabulator-group-level-2 {
      top: calc(2 * #{$group-header-height});
    }
    &.tabulator-group-level-3 {
      top: calc(3 * #{$group-header-height});
    }
    &.tabulator-group-level-4 {
      top: calc(4 * #{$group-header-height});
    }
    &.tabulator-group-level-5 {
      top: calc(5 * #{$group-header-height});
    }
  }
}

</style>
