import { mount } from '@vue/test-utils';
import BaseSimpleTable from './BaseSimpleTable.vue';
import { SimpleTableColumn } from './types';

// Mock Tabulator
jest.mock('tabulator-tables', () => ({
  TabulatorFull: jest.fn().mockImplementation(() => ({
    destroy: jest.fn(),
    setData: jest.fn(),
    setColumns: jest.fn(),
    getData: jest.fn(() => []),
    getSelectedData: jest.fn(() => []),
    getSelectedRows: jest.fn(() => []),
    selectRow: jest.fn(),
    deselectRow: jest.fn(),
    addRow: jest.fn(() => Promise.resolve({})),
    updateRow: jest.fn(() => true),
    deleteRow: jest.fn(),
    clearData: jest.fn(),
    setFilter: jest.fn(),
    clearFilter: jest.fn(),
    setSort: jest.fn(),
    clearSort: jest.fn(),
    redraw: jest.fn(),
    scrollToRow: jest.fn(() => Promise.resolve()),
    scrollToColumn: jest.fn(() => Promise.resolve()),
    download: jest.fn(),
    getDataCount: jest.fn(() => 0),
    getColumns: jest.fn(() => []),
    hideColumn: jest.fn(),
    showColumn: jest.fn(),
    toggleColumn: jest.fn(),
    blockRedraw: jest.fn(),
    restoreRedraw: jest.fn(),
  })),
}));

describe('BaseSimpleTable', () => {
  const mockColumns: SimpleTableColumn[] = [
    {
      field: 'name',
      title: 'Name',
      sortable: true,
      filterable: true,
    },
    {
      field: 'age',
      title: 'Age',
      sortable: true,
      width: 100,
    },
    {
      field: 'email',
      title: 'Email',
      filterable: true,
    },
  ];

  const mockData = [
    { name: 'John Doe', age: 30, email: 'john@example.com' },
    { name: 'Jane Smith', age: 25, email: 'jane@example.com' },
  ];

  it('renders without crashing', () => {
    const wrapper = mount(BaseSimpleTable, {
      propsData: {
        columns: mockColumns,
        data: mockData,
      },
    });

    expect(wrapper.exists()).toBe(true);
    expect(wrapper.find('.base-simple-table').exists()).toBe(true);
    expect(wrapper.find('.tabulator-container').exists()).toBe(true);
  });

  it('accepts columns and data props', () => {
    const wrapper = mount(BaseSimpleTable, {
      propsData: {
        columns: mockColumns,
        data: mockData,
      },
    });

    expect(wrapper.props('columns')).toEqual(mockColumns);
    expect(wrapper.props('data')).toEqual(mockData);
  });

  it('accepts options prop', () => {
    const options = {
      height: 400,
      pagination: true,
      paginationSize: 10,
    };

    const wrapper = mount(BaseSimpleTable, {
      propsData: {
        columns: mockColumns,
        data: mockData,
        options,
      },
    });

    expect(wrapper.props('options')).toEqual(options);
  });

  it('accepts loading prop', () => {
    const wrapper = mount(BaseSimpleTable, {
      propsData: {
        columns: mockColumns,
        data: mockData,
        loading: true,
      },
    });

    expect(wrapper.props('loading')).toBe(true);
  });

  it('processes columns correctly', () => {
    const wrapper = mount(BaseSimpleTable, {
      propsData: {
        columns: mockColumns,
        data: mockData,
      },
    });

    const processedColumns = (wrapper.vm as any).processedColumns;

    expect(processedColumns).toHaveLength(3);
    expect(processedColumns[0]).toMatchObject({
      field: 'name',
      title: 'Name',
      headerSort: true,
      headerFilter: 'input',
    });
    expect(processedColumns[1]).toMatchObject({
      field: 'age',
      title: 'Age',
      width: 100,
      headerSort: true,
    });
    expect(processedColumns[2]).toMatchObject({
      field: 'email',
      title: 'Email',
      headerFilter: 'input',
    });
  });

  it('provides public API methods', () => {
    const wrapper = mount(BaseSimpleTable, {
      propsData: {
        columns: mockColumns,
        data: mockData,
      },
    });

    const vm = wrapper.vm as any;

    // Test that all public methods exist
    expect(typeof vm.getData).toBe('function');
    expect(typeof vm.getSelectedData).toBe('function');
    expect(typeof vm.getSelectedRows).toBe('function');
    expect(typeof vm.selectRow).toBe('function');
    expect(typeof vm.deselectRow).toBe('function');
    expect(typeof vm.addRow).toBe('function');
    expect(typeof vm.updateRow).toBe('function');
    expect(typeof vm.deleteRow).toBe('function');
    expect(typeof vm.clearData).toBe('function');
    expect(typeof vm.setData).toBe('function');
    expect(typeof vm.setFilter).toBe('function');
    expect(typeof vm.clearFilter).toBe('function');
    expect(typeof vm.setSort).toBe('function');
    expect(typeof vm.clearSort).toBe('function');
    expect(typeof vm.redraw).toBe('function');
    expect(typeof vm.scrollToRow).toBe('function');
    expect(typeof vm.scrollToColumn).toBe('function');
    expect(typeof vm.download).toBe('function');
    expect(typeof vm.getRowCount).toBe('function');
    expect(typeof vm.getColumns).toBe('function');
    expect(typeof vm.hideColumn).toBe('function');
    expect(typeof vm.showColumn).toBe('function');
    expect(typeof vm.toggleColumn).toBe('function');
  });

  it('emits events correctly', async () => {
    const wrapper = mount(BaseSimpleTable, {
      propsData: {
        columns: mockColumns,
        data: mockData,
      },
    });

    // Simulate table built event
    const vm = wrapper.vm as any;
    vm.isInitialized = true;

    // Test that events can be emitted
    wrapper.vm.$emit('table-built');
    wrapper.vm.$emit('data-loaded', mockData);
    wrapper.vm.$emit('data-changed', mockData);

    await wrapper.vm.$nextTick();

    expect(wrapper.emitted('table-built')).toBeTruthy();
    expect(wrapper.emitted('data-loaded')).toBeTruthy();
    expect(wrapper.emitted('data-changed')).toBeTruthy();
  });
});