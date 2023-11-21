<template>
  <div class="table-container">
    <div class="--button">
      <button id="toggle-column-freeze">Toggle Column Freeze</button>
    </div>
    
    <div ref="table" class="--table"></div>
  </div>
</template>

<script>
import { TabulatorFull as Tabulator } from 'tabulator-tables';
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
        this.$nuxt.$emit('on-update-response-tabledata', JSON.stringify(json));
      }
    },
    editableConfig() {
      if (this.editable) {
        return {
          editor: "textarea",
          editorParams: {
            selectContents: true,
          },
          cellEdited: (cell) => {
            this.tableJSON.data = this.table.getData();
            this.tableJSON = this.tableJSON  // Trigger the setter
          }
        };
      }
      return {};
    },
    columns() {
      if (!this.tableJSON?.schema) return [];
      let primaryKey = this.tableJSON.schema.primaryKey;

      let columns = this.tableJSON.schema.fields.map((column, index) => ({
        title: column.name,
        field: column.name,
        headerSort: false,
        frozen: primaryKey?.length && primaryKey.includes(column.name),
        widthGrow: 0.5,
        ...this.editableConfig, // Spread the editableConfig here
      }));
      // columns.unshift({ rowHandle: true, formatter: "handle", headerSort: false, frozen: true, width: 30, minWidth: 30 },);
      
      return columns
    },
  },
  mounted() {
    this.table = new Tabulator(this.$refs.table, {
      persistence: {
        columns: true,
      },
      data: this.tableJSON.data,
      tabEndNewRow: true,
      reactiveData: true,
      // clipboard: true,
      // clipboardPasteAction: "replace",
      // autoColumns: true,
      columns: this.columns,
      resizableColumnFit: true,
      layout: "fitDataTable",
    });
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

  .--button {
    display: inline-block;
    padding: 10px 0px;
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