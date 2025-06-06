// Mock implementation for tabulator-tables
export class TabulatorFull {
  constructor() {
    this.rows = [];
    this.columns = [];
    this.data = [];
    // Mock all required methods to prevent errors
    this.initialized = true;
  }

  addRow(data, position, index) {
    const newRow = { 
      _row: { data },
      getData: () => data,
      getElement: () => document.createElement("div"),
      getTable: () => this,
      delete: () => true
    };
    this.rows.push(newRow);
    this.data.push(data);
    return newRow;
  }

  getRows() {
    return this.rows;
  }

  getData() {
    return this.data;
  }

  getColumns() {
    return this.columns.map(col => ({
      getField: () => col.field,
      getDefinition: () => col,
      getElement: () => document.createElement("div"),
      getTable: () => this,
      updateDefinition: () => true
    }));
  }

  deleteRow() {
    return true;
  }

  clearData() {
    this.rows = [];
    this.data = [];
    return true;
  }

  updateData() {
    return true;
  }

  validate() {
    return true;
  }

  setData(data) {
    this.data = data || [];
    this.rows = data ? data.map(item => ({ 
      data: item, 
      _row: { data: item },
      getData: () => item,
      getElement: () => document.createElement("div")
    })) : [];
    return true;
  }

  on() {
    return this;
  }

  redraw() {
    return true;
  }

  updateColumnDefinition() {
    return true;
  }

  getDataCount() {
    return this.data.length;
  }

  setSort() {
    return this;
  }

  setFilter() {
    return this;
  }

  setPage() {
    return this;
  }

  setPageSize() {
    return this;
  }

  getPageSize() {
    return 10;
  }

  getPage() {
    return 1;
  }

  getPageMax() {
    return 1;
  }
}

// Column component needed by tests
export class ColumnComponent {
  constructor(field, title) {
    this.field = field;
    this.title = title;
  }

  getField() {
    return this.field;
  }

  getDefinition() {
    return {
      field: this.field,
      title: this.title
    };
  }

  updateDefinition() {
    return true;
  }
}

export default {
  TabulatorFull,
  ColumnComponent
};