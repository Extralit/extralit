<template>
  <div class="simple-table-example">
    <h3>BaseSimpleTable Example</h3>

    <div class="controls">
      <BaseButton @click="addSampleRow">Add Row</BaseButton>
      <BaseButton @click="clearTable">Clear Table</BaseButton>
      <BaseButton @click="toggleLoading">{{ loading ? 'Stop Loading' : 'Start Loading' }}</BaseButton>
      <BaseButton @click="exportData">Export CSV</BaseButton>
    </div>

    <BaseSimpleTable ref="simpleTable" :data="tableData" :columns="columns" :options="tableOptions" :loading="loading"
      @table-built="onTableBuilt" @row-click="onRowClick" @cell-edited="onCellEdited" @data-changed="onDataChanged" />

    <div v-if="selectedRow" class="selected-info">
      <h4>Selected Row:</h4>
      <pre>{{ JSON.stringify(selectedRow, null, 2) }}</pre>
    </div>
  </div>
</template>

<script lang="ts">
import BaseSimpleTable from './BaseSimpleTable.vue';
import { SimpleTableColumn, SimpleTableOptions } from './types';
import BaseButton from '../base-button/BaseButton.vue';

export default {
  name: "BaseSimpleTableExample",

  components: {
    BaseSimpleTable,
    BaseButton,
  },

  data() {
    return {
      loading: false,
      selectedRow: null,
      tableData: [
        {
          id: 1,
          reference: "Smith2023",
          title: "Machine Learning in Healthcare",
          authors: "Smith, J.; Johnson, A.",
          year: 2023,
          status: "add",
          doi: "10.1000/182",
        },
        {
          id: 2,
          reference: "Brown2022",
          title: "Deep Learning Applications",
          authors: "Brown, M.; Davis, K.",
          year: 2022,
          status: "update",
          doi: "10.1000/183",
        },
        {
          id: 3,
          reference: "Wilson2021",
          title: "Natural Language Processing",
          authors: "Wilson, R.; Taylor, S.",
          year: 2021,
          status: "skip",
          doi: "10.1000/184",
        },
      ],
      columns: [
        {
          field: "reference",
          title: "Reference",
          width: 120,
          sortable: true,
          filterable: true,
        },
        {
          field: "title",
          title: "Title",
          sortable: true,
          filterable: true,
          editor: "input",
        },
        {
          field: "authors",
          title: "Authors",
          sortable: true,
          filterable: true,
          editor: "textarea",
        },
        {
          field: "year",
          title: "Year",
          width: 80,
          sortable: true,
          filterable: true,
          editor: "number",
        },
        {
          field: "status",
          title: "Import Status",
          width: 120,
          sortable: true,
          filterable: true,
          editor: "select",
          editorParams: {
            values: ["add", "update", "skip", "failed"],
          },
          formatter: this.statusFormatter,
          cssClass: "status-column",
        },
        {
          field: "doi",
          title: "DOI",
          width: 120,
          sortable: true,
          filterable: true,
          editor: "input",
        },
      ] as SimpleTableColumn[],
      tableOptions: {
        height: 400,
        layout: "fitDataTable",
        pagination: true,
        paginationSize: 10,
        paginationSizeSelector: [5, 10, 20, 50],
        selectable: "highlight",
        movableRows: true,
        resizableColumns: true,
      } as SimpleTableOptions,
    };
  },

  methods: {
    statusFormatter(cell: any): string {
      const value = cell.getValue();
      const colors = {
        add: "#28a745",
        update: "#007bff",
        skip: "#6c757d",
        failed: "#dc3545",
      };

      const color = colors[value] || "#6c757d";
      return `<span style="color: ${color}; font-weight: 600;">${value.toUpperCase()}</span>`;
    },

    onTableBuilt() {
      console.log("Table built successfully");
    },

    onRowClick(e: Event, row: any) {
      this.selectedRow = row.getData();
      console.log("Row clicked:", this.selectedRow);
    },

    onCellEdited(cell: any) {
      console.log("Cell edited:", {
        field: cell.getField(),
        value: cell.getValue(),
        row: cell.getRow().getData(),
      });
    },

    onDataChanged(data: any[]) {
      console.log("Data changed:", data);
    },

    addSampleRow() {
      const newRow = {
        id: Date.now(),
        reference: `NewRef${Date.now()}`,
        title: "New Research Paper",
        authors: "New Author",
        year: 2024,
        status: "add",
        doi: `10.1000/${Date.now()}`,
      };

      (this.$refs.simpleTable as any).addRow(newRow);
    },

    clearTable() {
      (this.$refs.simpleTable as any).clearData();
    },

    toggleLoading() {
      this.loading = !this.loading;
    },

    exportData() {
      (this.$refs.simpleTable as any).download("csv", "table-data.csv");
    },
  },
};
</script>

<style lang="scss" scoped>
.simple-table-example {
  padding: $base-space * 2;

  h3 {
    margin-bottom: $base-space * 2;
    color: var(--fg-primary);
  }

  .controls {
    display: flex;
    gap: $base-space;
    margin-bottom: $base-space * 2;
    flex-wrap: wrap;
  }

  .selected-info {
    margin-top: $base-space * 2;
    padding: $base-space * 2;
    background: var(--bg-accent-grey-2);
    border: 1px solid var(--border-field);
    border-radius: $border-radius;

    h4 {
      margin: 0 0 $base-space 0;
      color: var(--fg-primary);
    }

    pre {
      margin: 0;
      font-size: 12px;
      color: var(--fg-secondary);
      white-space: pre-wrap;
      word-break: break-word;
    }
  }
}

:deep(.status-column) {
  text-align: center;
}
</style>