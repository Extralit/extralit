<template>
  <div class="table-container"
    @focusin="setFocus(true)" 
    @focusout="setFocus(false)"
  >
    <div class="__table-buttons">
      <BaseDropdown v-show="editable" :visible="dropdownEditTableVisible" >
        <span slot="dropdown-header">
          <BaseButton @click.prevent="dropdownEditTableVisible=!dropdownEditTableVisible">
            Edit table
            <svgicon name="chevron-down" width="8" height="8" />
          </BaseButton>
        </span>
        <span slot="dropdown-content">
          <BaseButton v-show="editable && tabulator" @click.prevent="tabulator.undo();">
            Undo
          </BaseButton>
          <BaseButton v-show="editable && tabulator" @click.prevent="tabulator.redo();">
            Redo
          </BaseButton>
          <BaseButton v-show="editable" @click.prevent="clearTable(); dropdownEditTableVisible=false">
            {{ tabulator?.getDataCount() > 0 ? 'Clear data' : 'Delete table' }}
          </BaseButton>
        </span>
      </BaseDropdown>

      <BaseDropdown v-show="editable && tabulator" :visible="visibleColumnDropdown" class="dropdown"  >
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

      <BaseButton v-show="editable && tabulator" @click.prevent="addRow()">
        ➕ Add Row
      </BaseButton>

      <BaseDropdown v-show="tabulator && columnValidators && Object.keys(columnValidators).length"
        :visible="editable && visibleCheckdropdown" >
        <span slot="dropdown-header">
          <BaseButton
            @click.prevent="validateTable({ scrollToError: true, saveData: true }); visibleCheckdropdown=!visibleCheckdropdown">
            Check data <i v-if="tableJSON?.schema?.is_latest === false">!</i>
          </BaseButton>
        </span>
        <span slot="dropdown-content">
          <BaseButton @click.prevent="$emit('updateValidValues', true);">
            Ignore errors
          </BaseButton>
          <BaseButton 
            v-if="tableJSON?.schema?.is_latest === false" 
            @click.prevent="fetchValidation({ latest: true });"
          >
            Fetch latest schema
          </BaseButton>
        </span>
      </BaseDropdown>
    </div>

    <div 
      ref="tabulator" 
      class="__table" 
      @keydown.enter.prevent
    />

  </div>
</template>

<script lang="ts">
import { merge } from 'lodash';
import { CellComponent, ColumnComponent, GroupComponent, RangeComponent, RowComponent, TabulatorFull as Tabulator } from "tabulator-tables";
import "tabulator-tables/dist/css/tabulator.min.css";
import { getColumnValidators, getColumnEditorParams } from "./validationUtils";
import { cellTooltip, headerTooltip, groupHeader, getRangeRowData, getRangeColumns } from "./tableUtils"; 
import { useSchemaTableViewModel } from "./useSchemaTableViewModel";
import { useLLMExtractionViewModel } from "./useLLMExtractionViewModel";
import { useReferenceTablesViewModel } from "./useReferenceTablesViewModel";
import { Data, TableData } from '@/v1/domain/entities/table/TableData';
import { DataFrameField } from '@/v1/domain/entities/table/Schema';
import { Question } from "@/v1/domain/entities/question/Question";
import { difference } from '@/v1/domain/entities/record/Record';
import { Validators } from '~/v1/domain/entities/table/Validation';

export default {
  props: {
    tableJSON: {
      type: Object as () => TableData,
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
      tabulator: null,
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
      immediate: false,
      handler(newTableJSON: TableData, oldTableJSON: TableData) {
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
          if (this.editable) console.warn('Changes columns config', difference(newColumnsConfig, oldColumnsConfig));
        }
      },
    },
    validation: {
      handler(newValidation, oldValidation) {
        if (this.isLoaded) {
          if (this.editable) console.warn('Changes validation', this.tableJSON.schema.schemaName, this.tableJSON.schema.version_tag);
          this.tabulator?.setColumns(this.columnsConfig);
          this.validateTable();
        }
      },
    },
  },

  created() {
    this.fetchValidation()
      .catch((error) => {
        console.error(`Failed to fetch validation: ${error}`);
        this.$notification.notify({
          message: `${error.response}: ${error.message}`,
          type: "error",
          onClick() {
            this.$notification.clear();
          },
        });
      })
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
      return this.tabulator?.getColumns()
        ?.map((col: ColumnComponent) => col.getField())
        ?.filter((field: string) => field && !field.startsWith('_')) || [];
    },
    columnsConfig() {
      if (!this.tableJSON?.schema) return [];

      var configs = this.tableJSON.schema.fields.map((column: DataFrameField) => {
        const commonConfig = this.generateColumnConfig(column.name);
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
      const indexerColumn = {
        title: "_id",
        field: "_id",
        visible: false,
        mutator: (value, data, type, params, component) => {
          if (type === "edit") {
            return value;
          } else if (value != null) {
            return value;
          }
          const maxRefValue = this.getColumnMaxValue(component.getField(), this.tabulator.getData());
          if (rownum < maxRefValue) {
            rownum = maxRefValue+1;
          }
          return rownum++;
        },
      };

      return [indexerColumn, ...configs];
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
            action: (e, group: GroupComponent) => {
              group.popup(`${group.getField()}: ${group.getKey()}`, "right");
            }
          },
          {
            separator: true,
          },
          {
            label: (group) => {
              const subGroupFields = (this.groupbyColumns.slice(group._group.level + 1));
              return `Add missing <b>${subGroupFields.join(', ')}</b> references`;
            },
            disabled: (group) => {
              if (!this.editable || !this.referenceValues) {
                return true;
              } else if (group._group.level + 1 >= this.groupbyColumns.length) {
                return true;
              }
              return false;
            },
            action: (e, group: GroupComponent) => {
              let parentGroup = group.getParentGroup();
              const fixedValues: Record<string, string> = { [group.getField()]: group.getKey() };

              while (parentGroup) {
                fixedValues[parentGroup.getField()] = parentGroup.getKey();
                parentGroup = parentGroup.getParentGroup();
              }
              const combinations = this.generateCombinations(this.referenceValues, fixedValues);

              combinations.filter((rowData) => {
                return !group.getSubGroups().some((subGroup: GroupComponent) => {
                  return subGroup.getKey() === rowData[subGroup.getField()];
                });
              }).forEach(rowData => {
                this.addRow(null, rowData);
              });
            }
          },
          {
            label: "Delete rows group",
            disabled: !this.editable,
            action: (e, group: GroupComponent) => {
              this.deleteGroupRows(group);
              this.updateTableJsonData();
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

          this.tabulator.rowManager.rows.forEach((row)=>{
            removeColumns.forEach((field) => {
              row.deleteCell(field);
              this.$delete(row.data, field)
            });
          })

          // Remove removeColumns from this.tableJSON.data
          this.tableJSON.data.forEach((row) => {
            removeColumns.forEach((field) => {
              this.$delete(row, field);
            });
          });
        }
      }

      if (add) {
        const addColumns = this.columns.filter(
          (field) => !this.tableJSON.schema.fields.map((field) => field.name).includes(field) && field != undefined);

        // Add the new field to the schema
        const data = this.tabulator.getData().map(({ _id, ...rest }) => rest)
        data.forEach((item) => {
          addColumns.forEach((column) => {
            item[column] = null;
          });
        });

        this.tabulator.setData(data);
        addColumns.forEach((column) => {
          this.tableJSON.schema.fields.push({
            name: column,
            type: "string",
          });
        });
      }

      if (update) {
        // Update the field name for all data
        const data = this.tabulator.getData().map(({ _id, ...rest }) => rest)
        data.forEach((row) => {
          row[newFieldName] = row[oldFieldName];
          delete row[oldFieldName];
        });
        this.tabulator.setData(data);

        this.tabulator.updateColumnDefinition(oldFieldName, {
          field: newFieldName,
          title: newFieldName,
          ...this.generateColumnConfig(newFieldName),
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
      
      this.tableJSON.data = this.tabulator.getData().map(({ _id, ...rest }) => rest);
    },
    isIndexRefColumn(field: string) { 
      return this.indexColumns?.includes(field) || this.refColumns?.includes(field);
    },
    generateColumnConfig(field: string) {
      const hide = !this.showRefColumns && this.isIndexRefColumn(field);
      const commonConfig = {
        title: field,
        field: field,
        visible: !hide,
        width: this.isIndexRefColumn(field) ? 50 : undefined,
        validator: this.columnValidators[field],
        formatter: (cell: CellComponent, formatterParams, onRendered): any => {
          const value = cell.getValue();
          const cellElement = cell.getElement();
          if (this.isIndexRefColumn(field)) {
            cellElement.style.fontWeight = "bold";
          } else if (value === "NA" || value === "ND") {
            cellElement.style.color = "#999";
          } else {
            cellElement.style.color = "";
          }
          return value;
        },
      };
      return commonConfig;
    },
    generateColumnEditableConfig(field: string) {
      if (!this.editable) return {};

      // Default editable config for a column
      let config = {
        editorParams: {
          search: true,
          autocomplete: true,
          selectContents: true,
        },
        // headerDblClick: function(e, column) {
        //   // Enable editable title on double click
        //   if (column.getDefinition().frozen || column.getDefinition().editableTitle) return
        //   column.updateDefinition({ editableTitle: true });
        // },
      };

      config = merge({}, config, getColumnEditorParams(field, this.validation, this.refColumns, this.referenceValues));

      return config;
    },
    validateTable(options: { scrollToError?: boolean, saveData?: boolean }): boolean {
      var validErrors = this.tabulator.validate();

      const isValid = validErrors === true;
      this.$emit("updateValidValues", isValid);
      if (isValid) {
        return true;
      } else {
        const cellsWithNA = validErrors.filter((cell: CellComponent) => cell.getValue() == "NA");
        if (cellsWithNA.length > 0) {
          this.tabulator.clearCellValidation(cellsWithNA);
        }
      }

      if (options?.scrollToError == true) {
        const firstErrorCell = validErrors[0];
        this.tabulator.scrollToRow(firstErrorCell._cell.row);
        this.tabulator.scrollToColumn(firstErrorCell._cell.column.field, 'middle');
      }

      if (options?.saveData == true) {
        this.updateTableJsonData();
      }

      return isValid;
    },
    toggleShowRefColumns() {
      this.showRefColumns = !this.showRefColumns;
      this.tabulator?.setColumns(this.columnsConfig);
    },
    columnMoved(column: ColumnComponent, columns: ColumnComponent[]) {
      this.tableJSON.schema.fields.sort((a, b) => {
        const aIndex = columns.findIndex((col) => col.getField() === a.name);
        const bIndex = columns.findIndex((col) => col.getField() === b.name);
        return aIndex - bIndex;
      });
    },
    async addRow(selectedRow?: RowComponent, rowData: Record<string, any>={}): Promise<RowComponent> {
      // const requiredFields = this.refColumns || this.indexColumns;
      // Select the last row if no row is selected
      if (!selectedRow) {
        selectedRow = this.tabulator.getRows()[this.tabulator.getRows().length - 1];
      }
      delete rowData._id;
      
      for (const field of this.columns) {
        if (rowData[field] != undefined) {
          continue
        } else if (this.indexColumns.includes(field) && !this.refColumns.includes(field) && 
            selectedRow?.getData()[field]) {
          const maxRefValue = this.getColumnMaxValue(field, this.tabulator.getData());
          rowData[field] = this.incrementReferenceStr(maxRefValue);
        } else if (this.refColumns.includes(field) && selectedRow?.getData()[field]) {
          rowData[field] = selectedRow?.getData()[field];
        } else {
          rowData[field] = undefined;
        }
      }
      const addedRow: RowComponent = await this.tabulator.addRow(rowData, false, selectedRow);
      this.updateTableJsonData();
      this.validateTable();
      if (!this.showRefColumns) this.toggleShowRefColumns();
      return addedRow;
      // const rowPos: number | boolean = selectedRow.getPosition()
      // if (typeof rowPos != 'number' || rowPos < 0 || rowPos > this.tableJSON.data.length) return
      // this.tableJSON.data.splice(rowPos-1, 0, rowData);
      // const addedRow: RowComponent = this.tabulator.getRowFromPosition(rowPos-1);
      // addedRow.validate();
      // return addedRow;
    },
    deleteGroupRows(group: GroupComponent) {
      group?.getRows()?.forEach((row: RowComponent) => {
        row?.delete();
      });

      group?.getSubGroups()?.forEach((subGroup: GroupComponent) => {
        this.deleteGroupRows(subGroup);
      });
    },
    async addColumn(selectedColumn?: ColumnComponent, newFieldName = "newColumn"): Promise<ColumnComponent> {
      const range: RangeComponent = this.tabulator.getRanges()[0];
      if (!selectedColumn) {
        if (range) {
          selectedColumn = range.getColumns()[0]
        }
      }
      // Assign a unique name to the new column
      let count = 1;
      while (this.columns.includes(newFieldName)) {
        newFieldName = `newColumn${count}`;
        count++;
      }
      
      let selectedColumnField = null;
      if (selectedColumn && selectedColumn?.getField()) {
        selectedColumnField = selectedColumn?.getField();
      }

      const column: ColumnComponent = await this.tabulator.addColumn(
        {
          ...this.generateColumnConfig(newFieldName),
          ...this.generateColumnEditableConfig(newFieldName),
          editableTitle: newFieldName.includes("newColumn"),
        }, 
        false, 
        selectedColumnField)

      this.updateTableJsonData(false, true);
      this.columnMoved(null, this.tabulator.getColumns());

      if (range) {
        const firstRow = range.getRows()[0];
        const cell = firstRow.getCell(newFieldName);
        cell.edit();
      }
      return column;

    },
    columnTitleChanged(column: ColumnComponent) {
      const newFieldName = column.getDefinition().title.replace('.', ' ');
      const oldFieldName = column.getDefinition().field;
      if (!newFieldName?.length || newFieldName == oldFieldName) return;
      if (this.columns.includes(newFieldName)) {
        setTimeout(() => {
          this.$notification.notify({
            message: `Column name '${newFieldName}' already exists. Please choose a different name.`,
            type: "warning",
            onClick() {
              this.$notification.clear();
            },
          });
        }, 500);
        return;
      }

      if (column.getDefinition().editableTitle) {
        // @ts-ignore
        column.updateDefinition({ editableTitle: false });
      }

      this.updateTableJsonData(false, false, true, newFieldName, oldFieldName);
      // this.tabulator?.setColumns(this.columnsConfig);
    },
    clearTable() {
      if (this.tabulator?.getDataCount() == 0) {
        this.tableJSON = undefined;
        return;
      }
      this.tabulator?.clearData()
      this.columns?.forEach((column) => {
        if (!this.refColumns.includes(column)) {
          this.tabulator?.deleteColumn(column);
        }
      });
    },
    addEmptyReferenceRows() {
      const combinations = this.generateCombinations(this.referenceValues);

      combinations.forEach(rowData => {
        this.addRow(null, rowData);
      });
    },
    async completionRange(range: RangeComponent) {
      const rangeData = getRangeRowData(range)
      const rangeColumns = getRangeColumns(range);
      const selectedRowData: Record<string, any> = Object.values(rangeData)
        .map(({ _id, ...rest }) => rest);

      this.completeExtraction(selectedRowData, rangeColumns, this.referenceValues)
        .then((predictedRowData: Data) => {
          this.updateRangeData(predictedRowData, range);
        })
        .catch((error) => {
          console.error(error)
          this.$notification.notify({
            message: `${error.message}`,
            type: "error",
            onClick() {
              this.$notification.clear();
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
              this.tabulator.modules.history.action("cellEdit", cell, {
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
          this.tabulator.updateData([{_id: index, ...dataUpdate}])
            .catch(function(error) {
              throw new Error(`Failed to update data: ${error.message} \n${JSON.stringify({_id: index, ...dataUpdate})}`);
            });
        }
      });

      this.updateTableJsonData();
      this.validateTable();
    },
    columnContextMenu() {
      let menu = [
        {
          label: function(column: ColumnComponent) {
            return !column.getDefinition().frozen ? "Freeze column": "Unfreeze column";
          },
          action: (e, column) => {
            column.updateDefinition({
              frozen: !column.getDefinition().frozen,
            });
          }
        },
        {
          label: "Filter values",
          action: (e, column: ColumnComponent) => {
            column.updateDefinition({
              // @ts-ignore
              headerFilter: !column.getDefinition().headerFilter,
            });
          }
        },
        {
          separator: true,
        },
        {
          label: "Add column ➡️",
          disabled: !this.editable,
          action: (e, column) => {
            this.addColumn(column);
          }
        },
        {
          label: "Rename column",
          disabled: !this.editable,
          action: function(e, column: ColumnComponent) {
            if (column.getDefinition().frozen) return;

            column.updateDefinition({
              editableTitle: !column.getDefinition().editableTitle,
              // @ts-ignore
              headerMenu: function(e, column: ColumnComponent) {
                return column.getDefinition().editableTitle ? [{
                  label: "Accept",
                  action: (e, column) => {
                    if (column.getDefinition().frozen) return;
                    column.updateDefinition({
                      editableTitle: !column.getDefinition().editableTitle,
                      headerMenu: null,
                    });
                  }
                }] : null;
              },
            });
          }
        },
        {
          label: "Delete column(s)",
          disabled: (column: ColumnComponent) => {
            if (!this.editable || column.getField() === "_id" || this.indexColumns.includes(column.getField()) || this.refColumns.includes(column.getField())) {
              return true;
            }
            return false;
          },
          action: (e, column: ColumnComponent) => {
            const range: RangeComponent = this.tabulator.getRanges()[0];
            if (range.getColumns().length > 1) {
              range.getColumns().forEach((column) => {
                column.delete();
              });
            } else {
              column.delete();
            }
            this.updateTableJsonData(true);
          }
        },
      ];
      return menu;
    },
    rowContextMenu() {
      let menu = [
        {
          label: "LLM fill-in",
          disabled: !this.editable,
          action: (e, row) => {
            const range = this.tabulator.getRanges()[0];
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
          label: "Duplicate row(s)",
          disabled: !this.editable,
          action: (e, row: RowComponent) => {
            const duplicateRows: RowComponent[] = this.tabulator.getRanges()[0]?.getRows();
            if (duplicateRows?.length > 0) {
              // A range of rows is selected
              var lastRowInSelection = duplicateRows[duplicateRows.length - 1];

              duplicateRows.reverse().forEach((row: RowComponent) => {
                const newRowData = { ...row.getData() };
                this.indexColumns.forEach((field: string) => {
                  newRowData[field] = undefined;
                });
                
                this.addRow(lastRowInSelection, newRowData);
              });
            } else {
              // Only a single row is selected
              const newRowData = { ...row.getData() };
              this.indexColumns.forEach((field: string) => {
                newRowData[field] = undefined;
              });
              this.addRow(row, newRowData);
            }
          }
        },
        {
          label: "Delete row(s)",
          disabled: !this.editable,
          action: (e, row: RowComponent) => {
            const range: RangeComponent = this.tabulator.getRanges()[0];

            if (range.getRows().length > 1) {
              range.getRows().forEach((row) => {
                row.delete();
              });
            } else {
              row.delete();
            }
            
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

      this.tabulator = new Tabulator(this.$refs.tabulator, {
        data: this.tableJSON.data,
        reactiveData: true,
        layout: this.columns.length <= 2 ? "fitData" : "fitDataTable",
        height: 'auto',
        // renderVertical: "basic",
        layoutColumnsOnNewData: false,
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
          formatter: "rownum", cssClass:"range-header-col",
        },
        rowContextMenu: this.rowContextMenu,
        index: "_id",
        ...this.groupConfigs,

        // Column
        columns: this.columnsConfig,
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
        selectableRows: false,
        selectableRange: 1,
        selectableRangeColumns: true,
        selectableRangeRows: false,
        selectableRangeClearCells: true,
        editTriggerEvent: this.editable ? "dblclick" : false,

        // configure clipboard to allow copy and paste of range format data
        clipboard: true,
        clipboardCopyRowRange: "range",
        clipboardPasteAction: this.editable ? "range" : null,
        clipboardPasteParser: this.editable ? "range" : null,
        clipboardCopyConfig: {
          rowHeaders: false,
          columnHeaders: false,
        },
        clipboardCopyStyled: false,

        // persistence
        persistence: this.editable ? {
          sort: true,
          filter: true,
          headerFilter: true,
          // columns: ["frozen"], 
          group: {
            groupBy: true,
            groupStartOpen: true,
            groupHeader: true,
          },
          page: true,
        } : false,
        persistenceID: `tabulator-${this.tableJSON.schema.schemaName}-${this.tableJSON.reference}`,

        validationMode: "highlight",
        history: this.editable,
      });

      if (this.editable) {
        this.tabulator.on("columnTitleChanged", this.columnTitleChanged.bind(this));

        this.tabulator.on("columnMoved", this.columnMoved.bind(this));

        this.tabulator.on("cellEdited", (cell: CellComponent) => {
          this.updateTableJsonData();
          // const rowPos: number | boolean = cell.getRow().getPosition();
          // if (typeof rowPos != 'number' || rowPos < 0 || rowPos > this.tableJSON.data.length) return;
          // this.$set(this.tableJSON.data[rowPos-1], cell.getColumn().getField(), cell.getValue());
        });

        this.tabulator.on("clipboardPasted", (clipboard, rowData, rows) => {
          this.updateTableJsonData();
          this.validateTable();
        });

        this.tabulator.on("historyUndo", (clipboard, rowData, rows) => {
          this.updateTableJsonData();
          this.validateTable();
        });

        this.tabulator.on("historyRedo", (clipboard, rowData, rows) => {
          this.updateTableJsonData();
          this.validateTable();
        });

        this.tabulator.on("validationFailed", function(cell: CellComponent, value, validators: Validators) {
          if (value === "NA") {
            cell.clearValidation();
          }
        });
      }

      this.tabulator.on("tableBuilt", () => {
        this.isLoaded = true;
        this.tabulator?.setColumns(this.columnsConfig);
        this.validateTable();
      }); 

    } catch (error) {
      const message = `Failed to load table: ${error}`;
      this.$notification.notify({
        message: message,
        numberOfChars: message.length,
        type: "error",
        onClick() {
          this.$notification.clear();
        },
      });
    }
  },

  setup(props) {
    return {
      ...useSchemaTableViewModel(props),
      ...useReferenceTablesViewModel(props),
      ...useLLMExtractionViewModel(props),
    };
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
  max-height: 80vh;
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
    margin-bottom: 5px;
    border-radius: 5px;
    text-decoration: none;

    .button {
      cursor: pointer;
      &:hover,
      &--active {
        background: var(--bg-opacity-4);
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
