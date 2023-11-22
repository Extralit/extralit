<template>
  <div class="table-container">
    <div class="--buttons">
      <button v-if="indexColumns?.length" id="toggle-column-freeze">Toggle Column Freeze</button>
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

      let columns = this.tableJSON.schema.fields.map((column, index) => ({
        title: column.name === 'index' && index === 0 ? '' : column.name,
        field: column.name,
        frozen: this.indexColumns?.length && this.indexColumns.includes(column.name),
        ...this.editableConfig,
      }));
      // columns.unshift({ rowHandle: true, formatter: "handle", headerSort: false, frozen: true, width: 30, minWidth: 30 },);
      
      return columns
    },
  },
  mounted() {
    const layout = this.columns.length <= 2 ? "fitColumns" : "fitDataTable"

    this.table = new Tabulator(this.$refs.table, {
      maxHeight: "40vh",
      persistence: {
        columns: true,
      },
      data: this.tableJSON.data,
      tabEndNewRow: true,
      reactiveData: true,
      clipboard: true,
      columnDefaults: {
        resizable: true,
        maxWidth: layout === 'fitDataTable' ? 150 : null,
        headerWordWrap: true,
        headerSort: false,
      },
      columns: this.columns,
      layout: layout,
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

  .--buttons {
    display: inline-block;
    padding: 0 5px 10px 0;
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