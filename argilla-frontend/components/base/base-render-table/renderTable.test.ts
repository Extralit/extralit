import { shallowMount } from "@vue/test-utils";

import { TabulatorFull as Tabulator } from "tabulator-tables";
import RenderTable from "./RenderTable.vue";
import { TableData } from "~/v1/domain/entities/table/TableData";
import { useSchemaTableViewModel } from "./useSchemaTableViewModel";


// Mock composables
jest.mock("./useSchemaTableViewModel", () => ({
  useSchemaTableViewModel: () => ({
    validation: { value: null },
    indexColumns: { value: [] },
    refColumns: { value: [] },
    groupbyColumns: { value: [] },
    fetchValidation: jest.fn().mockResolvedValue(undefined)
  })
}));

jest.mock("./useReferenceTablesViewModel", () => ({
  useReferenceTablesViewModel: () => ({
    referenceValues: { value: null },
    findMatchingRefValues: jest.fn(),
    getTableDataFromRecords: jest.fn(),
    generateCombinations: jest.fn(),
    incrementReferenceStr: jest.fn(),
    getColumnMaxValue: jest.fn()
  })
}));

jest.mock("./useLLMExtractionViewModel", () => ({
  useLLMExtractionViewModel: () => ({
    completeExtraction: jest.fn().mockResolvedValue(undefined)
  })
}));

describe('RenderTable', () => {
  let wrapper;
  const mockTableData: TableData = {
    data: [
      { col1: "value1", col2: "value2" },
      { col1: "value3", col2: "value4" }
    ],
    schema: {
      primaryKey: ["col1"],
      fields: [
        { name: "col1", type: "string" },
        { name: "col2", type: "string" }
      ]
    },
    
  };

  const mockNotification = {
    notify: jest.fn(),
    clear: jest.fn()
  };

  const options = {
    propsData: {
      tableJSON: mockTableData,
      editable: true,
      hasValidValues: true,
      questions: []
    },
    stubs: ['BaseButton', 'BaseDropdown', 'svgicon'],
    mocks: {
      $notification: mockNotification
    }
  };

  beforeEach(() => {
    wrapper = shallowMount(RenderTable, options);
  });

  afterEach(() => {
    jest.clearAllMocks();
    if (wrapper) {
      wrapper.destroy();
    }
  });

  it('renders correctly with initial props', () => {
    expect(wrapper.exists()).toBe(true);
    expect(wrapper.find('.table-container').exists()).toBe(true);
    expect(wrapper.props().editable).toBe(true);
  });

  it('shows error notification when table fails to load', () => {
    const error = new Error('Test error');
    wrapper.vm.tabulator = null;

    // Trigger mounted hook error
    wrapper.vm.$options.mounted[0].call(wrapper.vm);

  });

  it('initializes tabulator with correct config', () => {
    expect(Tabulator).toHaveBeenCalledWith(
      expect.any(Element),
      expect.objectContaining({
        data: mockTableData.data,
        reactiveData: true,
        movableRows: true,
        editTriggerEvent: "dblclick"
      })
    );
  });

  it('emits focus events', async () => {
    await wrapper.find('.table-container').trigger('focusin');
    expect(wrapper.emitted('on-change-focus')[0]).toEqual([true]);

    await wrapper.find('.table-container').trigger('focusout'); 
    expect(wrapper.emitted('on-change-focus')[1]).toEqual([false]);
  });

  it('handles adding new row', async () => {
    const mockAddRow = jest.fn();
    wrapper.vm.tabulator = {
      addRow: mockAddRow,
      getData: () => [],
      getRows: () => []
    };

    await wrapper.vm.addRow();
    expect(mockAddRow).toHaveBeenCalled();
  });

  it('handles clearing table', async () => {
    const mockClear = jest.fn();
    const mockGetCount = jest.fn(() => 0);
    wrapper.vm.tabulator = {
      clearData: mockClear,
      getDataCount: mockGetCount
    };

    await wrapper.vm.clearTable();
    expect(mockGetCount).toHaveBeenCalled();
    expect(mockClear).not.toHaveBeenCalled();
    expect(wrapper.vm.tableJSON).toBeUndefined();
  });

  it('validates table data', async () => {
    const mockValidate = jest.fn(() => true);
    wrapper.vm.tabulator = {
      validate: mockValidate
    };

    const result = await wrapper.vm.validateTable({});
    expect(mockValidate).toHaveBeenCalled();
    expect(result).toBe(true);
    expect(wrapper.emitted('updateValidValues')[0]).toEqual([true]);
  });

  it('handles column title changes', async () => {
    const mockColumn = {
      getDefinition: () => ({
        title: 'newTitle',  
        field: 'oldField'
      })
    };

    wrapper.vm.columns = ['col1'];
    await wrapper.vm.columnTitleChanged(mockColumn);
    expect(wrapper.emitted('updateValidValues')).toBeFalsy();
  });

  it('handles adding new column', async () => {
    const mockAddColumn = jest.fn();
    wrapper.vm.tabulator = {
      addColumn: mockAddColumn,
      getColumns: () => [],
      getRanges: () => [],
      getData: () => []
    };

    await wrapper.vm.addColumn();
    expect(mockAddColumn).toHaveBeenCalled();
  });

  it('creates proper column context menu', () => {
    const menu = wrapper.vm.columnContextMenu();
    expect(menu).toHaveLength(6);
    expect(menu[0].label).toBeDefined();
    expect(menu[3].label).toBe('Add column ➡️');
  });

  it('creates proper row context menu', () => {
    const menu = wrapper.vm.rowContextMenu();
    expect(menu).toHaveLength(5);
    expect(menu[0].label).toBe('LLM fill-in');
    expect(menu[2].label).toBe('Add row below');
  });
});