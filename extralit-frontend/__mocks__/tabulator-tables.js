// Mock implementation for tabulator-tables
export class TabulatorFull {
  // Test hooks: how many times the ctor ran (rebuild detection) and the latest instance
  // (so tests can fire its stored event handlers). Reset these in a test's beforeEach.
  static constructed = 0;
  static latest = null;

  constructor(element, options) {
    this.element = element;
    this.options = options || {};
    this.handlers = {};
    this.rows = [];
    this.columns = [];
    this.data = [];
    // Mock all required methods to prevent errors
    this.initialized = true;
    TabulatorFull.constructed += 1;
    TabulatorFull.latest = this;
  }

  // Fire a stored handler from a test, e.g. instance.emit("cellEdited", fakeCell).
  emit(event, ...args) {
    this.handlers[event]?.(...args);
  }

  addRow(data, position, index) {
    const newRow = {
      _row: { data },
      getData: () => data,
      getElement: () => document.createElement("div"),
      getTable: () => this,
      delete: () => true,
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
    return this.columns.map((col) => ({
      getField: () => col.field,
      getDefinition: () => col,
      getElement: () => document.createElement("div"),
      getTable: () => this,
      updateDefinition: () => true,
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
    this.rows = data
      ? data.map((item) => ({
          data: item,
          _row: { data: item },
          getData: () => item,
          getElement: () => document.createElement("div"),
        }))
      : [];
    return true;
  }

  on(event, callback) {
    this.handlers[event] = callback;
    return this;
  }

  destroy() {
    return true;
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
      title: this.title,
    };
  }

  updateDefinition() {
    return true;
  }
}

export default {
  TabulatorFull,
  ColumnComponent,
};
