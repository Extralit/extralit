# BaseSimpleTable

A reusable table component built on top of Tabulator.js, designed as a simpler alternative to the existing `base-render-table` component. This component provides essential table functionality with built-in sorting, filtering, and pagination.

## Features

- **Built-in Functionality**: Sorting, filtering, and pagination out of the box
- **Custom Column Renderers**: Support for custom formatters and cell renderers
- **Editable Cells**: Optional cell editing with various input types
- **Row Selection**: Single or multiple row selection
- **Responsive Design**: Adapts to different screen sizes
- **Theme Integration**: Matches the existing design system
- **Event Handling**: Comprehensive event system for user interactions
- **Export Support**: Built-in data export functionality

## Basic Usage

```vue
<template>
  <BaseSimpleTable
    :data="tableData"
    :columns="columns"
    :options="tableOptions"
    @row-click="onRowClick"
  />
</template>

<script>
import BaseSimpleTable from '@/components/base/base-simple-table/BaseSimpleTable.vue';

export default {
  components: {
    BaseSimpleTable,
  },

  data() {
    return {
      tableData: [
        { id: 1, name: 'John Doe', age: 30, email: 'john@example.com' },
        { id: 2, name: 'Jane Smith', age: 25, email: 'jane@example.com' },
      ],
      columns: [
        {
          field: 'name',
          title: 'Name',
          sortable: true,
          filterable: true,
        },
        {
          field: 'age',
          title: 'Age',
          width: 100,
          sortable: true,
        },
        {
          field: 'email',
          title: 'Email',
          filterable: true,
        },
      ],
      tableOptions: {
        height: 400,
        pagination: true,
        paginationSize: 20,
        selectable: 'highlight',
      },
    };
  },

  methods: {
    onRowClick(e, row) {
      console.log('Row clicked:', row.getData());
    },
  },
};
</script>
```

## Props

### `data` (Array, required)
The data array to display in the table.

### `columns` (Array<SimpleTableColumn>, required)
Column definitions for the table.

### `options` (SimpleTableOptions, optional)
Additional table configuration options.

### `loading` (Boolean, optional, default: false)
Shows loading state when true.

## Column Configuration

Each column object can have the following properties:

```typescript
interface SimpleTableColumn {
  field: string;           // Data field name
  title: string;           // Column header title
  width?: number;          // Fixed column width
  minWidth?: number;       // Minimum column width
  maxWidth?: number;       // Maximum column width
  resizable?: boolean;     // Allow column resizing (default: true)
  sortable?: boolean;      // Enable sorting (default: true)
  filterable?: boolean;    // Add header filter
  formatter?: string | function; // Custom cell formatter
  editor?: string | boolean;      // Cell editor type
  editorParams?: any;      // Editor configuration
  validator?: string | function;  // Cell validation
  headerFilter?: string;   // Header filter type
  cellClick?: function;    // Cell click handler
  cellDblClick?: function; // Cell double-click handler
  cssClass?: string;       // Custom CSS class
  visible?: boolean;       // Column visibility (default: true)
}
```

## Table Options

```typescript
interface SimpleTableOptions {
  height?: string | number;           // Table height
  layout?: "fitData" | "fitDataFill" | "fitDataStretch" | "fitDataTable" | "fitColumns";
  pagination?: boolean;               // Enable pagination
  paginationSize?: number;            // Rows per page
  paginationSizeSelector?: number[] | boolean; // Page size selector
  selectable?: boolean | number | "highlight"; // Row selection mode
  selectableRangeMode?: "click" | "drag";      // Selection method
  movableRows?: boolean;              // Allow row reordering
  movableColumns?: boolean;           // Allow column reordering
  resizableColumns?: boolean;         // Allow column resizing
  sortMode?: "local" | "remote";      // Sorting mode
  filterMode?: "local" | "remote";    // Filtering mode
  placeholder?: string;               // Empty table message
}
```

## Events

The component emits the following events:

- `table-built`: Fired when the table is fully initialized
- `data-loaded`: Fired when data is loaded
- `data-changed`: Fired when table data changes
- `row-click`: Fired when a row is clicked
- `row-dblclick`: Fired when a row is double-clicked
- `row-selected`: Fired when a row is selected
- `row-deselected`: Fired when a row is deselected
- `cell-edited`: Fired when a cell is edited
- `column-moved`: Fired when a column is moved
- `column-resized`: Fired when a column is resized
- `header-click`: Fired when a column header is clicked
- `header-dblclick`: Fired when a column header is double-clicked
- `error`: Fired when an error occurs

## Public Methods

The component exposes the following methods via template refs:

### Data Methods
- `getData()`: Get all table data
- `getSelectedData()`: Get selected row data
- `setData(data)`: Set table data
- `clearData()`: Clear all data
- `addRow(data, pos?, index?)`: Add a new row
- `updateRow(row, data)`: Update existing row
- `deleteRow(rows)`: Delete rows

### Selection Methods
- `getSelectedRows()`: Get selected row components
- `selectRow(rows)`: Select rows
- `deselectRow(rows?)`: Deselect rows

### Filtering and Sorting
- `setFilter(field, type, value)`: Set column filter
- `clearFilter(includeHeaderFilters?)`: Clear filters
- `setSort(sortList)`: Set column sorting
- `clearSort()`: Clear sorting

### Display Methods
- `redraw(force?)`: Redraw table
- `scrollToRow(row, position?, ifVisible?)`: Scroll to row
- `scrollToColumn(column, position?, ifVisible?)`: Scroll to column
- `hideColumn(column)`: Hide column
- `showColumn(column)`: Show column
- `toggleColumn(column)`: Toggle column visibility

### Utility Methods
- `getRowCount()`: Get total row count
- `getColumns()`: Get column definitions
- `download(type, filename?, options?)`: Export table data

## Styling

The component uses CSS custom properties from the design system and can be customized by overriding these variables:

```scss
:deep(.tabulator) {
  // Custom styles here
}
```

## Example with Custom Formatter

```vue
<template>
  <BaseSimpleTable
    :data="data"
    :columns="columns"
  />
</template>

<script>
export default {
  data() {
    return {
      data: [
        { name: 'John', status: 'active' },
        { name: 'Jane', status: 'inactive' },
      ],
      columns: [
        { field: 'name', title: 'Name' },
        {
          field: 'status',
          title: 'Status',
          formatter: this.statusFormatter,
        },
      ],
    };
  },

  methods: {
    statusFormatter(cell) {
      const value = cell.getValue();
      const color = value === 'active' ? 'green' : 'red';
      return `<span style="color: ${color}">${value}</span>`;
    },
  },
};
</script>
```

## Dependencies

- `tabulator-tables`: ^6.2.1
- Semantic UI CSS theme for Tabulator

## Browser Support

Supports all modern browsers that support ES6+ and CSS Grid.