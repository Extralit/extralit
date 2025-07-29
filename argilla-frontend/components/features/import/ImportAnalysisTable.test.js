import { mount } from '@vue/test-utils';
import ImportAnalysisTable from './ImportAnalysisTable.vue';

// Mock BaseSimpleTable
jest.mock('@/components/base/base-simple-table/BaseSimpleTable.vue', () => ({
  name: 'BaseSimpleTable',
  template: '<div class="mock-base-simple-table"></div>',
  props: ['data', 'columns', 'options'],
}));

// Mock BaseSpinner
jest.mock('@/components/base/base-spinner/BaseSpinner.vue', () => ({
  name: 'BaseSpinner',
  template: '<div class="mock-base-spinner"></div>',
}));

// Mock BaseIcon
jest.mock('@/components/base/base-icon/BaseIcon.vue', () => ({
  name: 'BaseIcon',
  template: '<div class="mock-base-icon"></div>',
  props: ['name'],
}));

// Mock BaseButton
jest.mock('@/components/base/base-button/BaseButton.vue', () => ({
  name: 'BaseButton',
  template: '<button class="mock-base-button"><slot></slot></button>',
  props: ['variant', 'disabled'],
}));

describe('ImportAnalysisTable', () => {
  const mockAnalysisData = {
    documents: {
      'ref1': {
        document_create: {
          title: 'Test Document 1',
          authors: ['Author 1', 'Author 2'],
          year: '2023',
        },
        associated_files: ['file1.pdf'],
        status: 'add',
        validation_errors: [],
      },
      'ref2': {
        document_create: {
          title: 'Test Document 2',
          authors: ['Author 3'],
          year: '2024',
        },
        associated_files: ['file2.pdf', 'file3.pdf'],
        status: 'update',
        validation_errors: [],
      },
      'ref3': {
        document_create: {
          title: 'Test Document 3',
          authors: ['Author 4'],
          year: '2022',
        },
        associated_files: [],
        status: 'failed',
        validation_errors: ['Missing PDF file'],
      },
    },
    summary: {
      total_documents: 3,
      add_count: 1,
      update_count: 1,
      skip_count: 0,
      failed_count: 1,
    },
  };

  const mockDataframeData = {
    schema: {
      fields: [
        { name: 'reference', type: 'string' },
        { name: 'title', type: 'string' },
        { name: 'authors', type: 'string' },
        { name: 'year', type: 'string' },
      ],
      primaryKey: ['reference'],
    },
    data: [
      {
        reference: 'Smith2023',
        title: 'A Study on Machine Learning',
        authors: 'John Smith, Jane Doe',
        year: '2023',
      },
      {
        reference: 'Brown2024',
        title: 'Deep Learning Applications',
        authors: 'Alice Brown',
        year: '2024',
      },
    ],
  };

  it('renders without crashing', () => {
    const wrapper = mount(ImportAnalysisTable, {
      propsData: {
        analysisData: mockAnalysisData,
        loading: false,
      },
    });

    expect(wrapper.exists()).toBe(true);
    expect(wrapper.find('.import-analysis-table').exists()).toBe(true);
  });

  it('renders with dataframe data', () => {
    const wrapper = mount(ImportAnalysisTable, {
      propsData: {
        analysisData: mockAnalysisData,
        dataframeData: mockDataframeData,
        loading: false,
      },
    });

    expect(wrapper.exists()).toBe(true);
    expect(wrapper.find('.import-analysis-table').exists()).toBe(true);

    // Should show dataframe data in table
    const tableData = wrapper.vm.tableData;
    expect(tableData).toHaveLength(2);
    expect(tableData[0].reference).toBe('Smith2023');
    expect(tableData[0].title).toBe('A Study on Machine Learning');
  });

  it('shows loading state when loading prop is true', () => {
    const wrapper = mount(ImportAnalysisTable, {
      propsData: {
        analysisData: mockAnalysisData,
        loading: true,
      },
    });

    expect(wrapper.find('.loading-state').exists()).toBe(true);
    expect(wrapper.find('.mock-base-spinner').exists()).toBe(true);
    expect(wrapper.text()).toContain('Analyzing import status...');
  });

  it('shows error state when hasError is true', async () => {
    const wrapper = mount(ImportAnalysisTable, {
      propsData: {
        analysisData: mockAnalysisData,
        loading: false,
      },
    });

    // Set error state
    wrapper.vm.hasError = true;
    wrapper.vm.errorMessage = 'Test error message';
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.error-state').exists()).toBe(true);
    expect(wrapper.text()).toContain('Analysis Failed');
    expect(wrapper.text()).toContain('Test error message');
  });

  it('displays analysis summary correctly', () => {
    const wrapper = mount(ImportAnalysisTable, {
      propsData: {
        analysisData: mockAnalysisData,
        loading: false,
      },
    });

    const summaryStats = wrapper.find('.summary-stats');
    expect(summaryStats.exists()).toBe(true);

    expect(wrapper.text()).toContain('Total: 3');
    expect(wrapper.text()).toContain('Add: 1');
    expect(wrapper.text()).toContain('Update: 1');
    expect(wrapper.text()).toContain('Skip: 0');
    expect(wrapper.text()).toContain('Failed: 1');
  });

  it('generates table data correctly', () => {
    const wrapper = mount(ImportAnalysisTable, {
      propsData: {
        analysisData: mockAnalysisData,
        loading: false,
      },
    });

    const tableData = wrapper.vm.tableData;
    expect(tableData).toHaveLength(3);

    expect(tableData[0]).toMatchObject({
      reference: 'ref1',
      title: 'Test Document 1',
      authors: 'Author 1, Author 2',
      year: '2023',
      files: 'file1.pdf',
      status: 'add',
      originalStatus: 'add',
      canToggle: true,
    });

    expect(tableData[1]).toMatchObject({
      reference: 'ref2',
      title: 'Test Document 2',
      authors: 'Author 3',
      year: '2024',
      files: 'file2.pdf, file3.pdf',
      status: 'update',
      originalStatus: 'update',
      canToggle: true,
    });

    expect(tableData[2]).toMatchObject({
      reference: 'ref3',
      title: 'Test Document 3',
      authors: 'Author 4',
      year: '2022',
      files: 'No files',
      status: 'failed',
      originalStatus: 'failed',
      canToggle: false,
    });
  });

  it('generates table columns correctly', () => {
    const wrapper = mount(ImportAnalysisTable, {
      propsData: {
        analysisData: mockAnalysisData,
        loading: false,
      },
    });

    const columns = wrapper.vm.tableColumns;
    expect(columns).toHaveLength(6);

    expect(columns[0]).toMatchObject({
      field: 'reference',
      title: 'Reference',
      width: 150,
      frozen: true,
    });

    expect(columns[5]).toMatchObject({
      field: 'status',
      title: 'Import Status',
      width: 150,
      frozen: true,
    });
  });

  it('calculates confirmed count correctly', () => {
    const wrapper = mount(ImportAnalysisTable, {
      propsData: {
        analysisData: mockAnalysisData,
        loading: false,
      },
    });

    // Initially should count add and update documents
    expect(wrapper.vm.confirmedCount).toBe(2);

    // Change one document to ignore
    wrapper.vm.documentActions = { 'ref1': 'ignore' };
    expect(wrapper.vm.confirmedCount).toBe(1);
  });

  it('handles status toggle correctly', () => {
    const wrapper = mount(ImportAnalysisTable, {
      propsData: {
        analysisData: mockAnalysisData,
        loading: false,
      },
    });

    // Mock cell object
    const mockCell = {
      getValue: () => 'add',
      getRow: () => ({
        getData: () => ({
          status: 'add',
          originalStatus: 'add',
          reference: 'ref1',
          canToggle: true,
        }),
        update: jest.fn(),
      }),
    };

    // Test status toggle
    wrapper.vm.handleStatusClick({}, mockCell);

    expect(wrapper.vm.documentActions['ref1']).toBe('ignore');
    expect(mockCell.getRow().update).toHaveBeenCalledWith({ status: 'ignore' });
  });

  it('emits update event when document actions change', () => {
    const wrapper = mount(ImportAnalysisTable, {
      propsData: {
        analysisData: mockAnalysisData,
        loading: false,
      },
    });

    wrapper.vm.emitUpdate();

    expect(wrapper.emitted('update')).toBeTruthy();
    const updateEvent = wrapper.emitted('update')[0][0];

    expect(updateEvent).toHaveProperty('confirmedDocuments');
    expect(updateEvent).toHaveProperty('totalConfirmed');
    expect(updateEvent).toHaveProperty('documentActions');
  });

  it('handles cancel action correctly', () => {
    const wrapper = mount(ImportAnalysisTable, {
      propsData: {
        analysisData: mockAnalysisData,
        loading: false,
      },
    });

    // Set some document actions
    wrapper.vm.documentActions = { 'ref1': 'ignore' };

    // Cancel should reset actions
    wrapper.vm.handleCancel();

    expect(wrapper.vm.documentActions).toEqual({});
  });

  it('handles confirm import correctly', () => {
    const wrapper = mount(ImportAnalysisTable, {
      propsData: {
        analysisData: mockAnalysisData,
        loading: false,
      },
    });

    wrapper.vm.handleConfirmImport();

    expect(wrapper.emitted('update')).toBeTruthy();
  });

  it('formats authors correctly', () => {
    const wrapper = mount(ImportAnalysisTable, {
      propsData: {
        analysisData: mockAnalysisData,
        loading: false,
      },
    });

    expect(wrapper.vm.formatAuthors(['Author 1', 'Author 2'])).toBe('Author 1, Author 2');
    expect(wrapper.vm.formatAuthors('Single Author')).toBe('Single Author');
    expect(wrapper.vm.formatAuthors([])).toBe('N/A');
    expect(wrapper.vm.formatAuthors(null)).toBe('N/A');
  });

  it('formats files correctly', () => {
    const wrapper = mount(ImportAnalysisTable, {
      propsData: {
        analysisData: mockAnalysisData,
        loading: false,
      },
    });

    expect(wrapper.vm.formatFiles(['file1.pdf', 'file2.pdf'])).toBe('file1.pdf, file2.pdf');
    expect(wrapper.vm.formatFiles([])).toBe('No files');
    expect(wrapper.vm.formatFiles(null)).toBe('No files');
  });

  it('determines toggle capability correctly', () => {
    const wrapper = mount(ImportAnalysisTable, {
      propsData: {
        analysisData: mockAnalysisData,
        loading: false,
      },
    });

    expect(wrapper.vm.canToggleStatus('add')).toBe(true);
    expect(wrapper.vm.canToggleStatus('update')).toBe(true);
    expect(wrapper.vm.canToggleStatus('skip')).toBe(false);
    expect(wrapper.vm.canToggleStatus('failed')).toBe(false);
  });

  it('resets state correctly', () => {
    const wrapper = mount(ImportAnalysisTable, {
      propsData: {
        analysisData: mockAnalysisData,
        loading: false,
      },
    });

    // Set some state
    wrapper.vm.hasError = true;
    wrapper.vm.errorMessage = 'Test error';
    wrapper.vm.documentActions = { 'ref1': 'ignore' };

    // Reset
    wrapper.vm.reset();

    expect(wrapper.vm.hasError).toBe(false);
    expect(wrapper.vm.errorMessage).toBe('');
    expect(wrapper.vm.documentActions).toEqual({});
  });
});