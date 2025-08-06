import { mount } from "@vue/test-utils";
import ImportAnalysisTable from "./ImportAnalysisTable.vue";

// Mock BaseSimpleTable
jest.mock("@/components/base/base-simple-table/BaseSimpleTable.vue", () => ({
  name: "BaseSimpleTable",
  template: '<div class="mock-base-simple-table"></div>',
  props: ["data", "columns", "options"],
}));

// Mock BaseSpinner
jest.mock("@/components/base/base-spinner/BaseSpinner.vue", () => ({
  name: "BaseSpinner",
  template: '<div class="mock-base-spinner"></div>',
}));

// Mock BaseIcon
jest.mock("@/components/base/base-icon/BaseIcon.vue", () => ({
  name: "BaseIcon",
  template: '<div class="mock-base-icon"></div>',
  props: ["iconName"],
}));

// Mock BaseButton
jest.mock("@/components/base/base-button/BaseButton.vue", () => ({
  name: "BaseButton",
  template: '<button class="mock-base-button"><slot></slot></button>',
  props: ["variant", "disabled"],
}));

// Mock the view model
const mockViewModel = {
  isAnalyzing: false,
  hasError: false,
  errorMessage: "",
  analysisResult: null,
  documentActions: {},
  reset: jest.fn(),
  analyzeImport: jest.fn(),
  retryAnalysis: jest.fn(),
};

jest.mock("./useImportAnalysisViewModel", () => ({
  useImportAnalysisViewModel: jest.fn(() => mockViewModel),
}));

describe("ImportAnalysisTable", () => {
  const mockAnalysisResult = {
    documents: {
      ref1: {
        document_create: {
          title: "Test Document 1",
          authors: ["Author 1", "Author 2"],
          year: "2023",
        },
        associated_files: ["file1.pdf"],
        status: "add",
        validation_errors: [],
      },
      ref2: {
        document_create: {
          title: "Test Document 2",
          authors: ["Author 3"],
          year: "2024",
        },
        associated_files: ["file2.pdf", "file3.pdf"],
        status: "update",
        validation_errors: [],
      },
      ref3: {
        document_create: {
          title: "Test Document 3",
          authors: ["Author 4"],
          year: "2022",
        },
        associated_files: [],
        status: "failed",
        validation_errors: ["Missing PDF file"],
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
        { name: "reference", type: "string" },
        { name: "title", type: "string" },
        { name: "authors", type: "string" },
        { name: "year", type: "string" },
      ],
      primaryKey: ["reference"],
    },
    data: [
      {
        reference: "Smith2023",
        title: "A Study on Machine Learning",
        authors: "John Smith, Jane Doe",
        year: "2023",
      },
      {
        reference: "Brown2024",
        title: "Deep Learning Applications",
        authors: "Alice Brown",
        year: "2024",
      },
    ],
  };

  const mockWorkspace = {
    id: "workspace-1",
    name: "Test Workspace",
  };

  const mockPdfData = {
    matchedFiles: [
      { file: { name: "file1.pdf", size: 1024 } },
      { file: { name: "file2.pdf", size: 2048 } },
    ],
  };

  // Common mount options with stubs
  const createMountOptions = (propsData = {}) => ({
    propsData: {
      dataframeData: mockDataframeData,
      pdfData: mockPdfData,
      workspace: mockWorkspace,
      loading: false,
      ...propsData,
    },
    stubs: {
      BaseSimpleTable: {
        template: '<div class="mock-base-simple-table"></div>',
        props: ["data", "columns", "options"],
      },
      BaseSpinner: {
        template: '<div class="mock-base-spinner"></div>',
      },
      BaseIcon: {
        template: '<div class="mock-base-icon"></div>',
        props: ["iconName"],
      },
      BaseButton: {
        template: '<button class="mock-base-button"><slot></slot></button>',
        props: ["variant", "disabled"],
      },
    },
  });

  beforeEach(() => {
    // Reset mock state before each test
    mockViewModel.isAnalyzing = false;
    mockViewModel.hasError = false;
    mockViewModel.errorMessage = "";
    mockViewModel.analysisResult = null;
    mockViewModel.documentActions = {};
    mockViewModel.reset.mockClear();
    mockViewModel.analyzeImport.mockClear();
    mockViewModel.retryAnalysis.mockClear();
  });

  it("renders without crashing", () => {
    const wrapper = mount(ImportAnalysisTable, createMountOptions());

    expect(wrapper.exists()).toBe(true);
    expect(wrapper.find(".import-analysis-table").exists()).toBe(true);
  });

  it("renders with dataframe data", () => {
    const wrapper = mount(ImportAnalysisTable, createMountOptions());

    expect(wrapper.exists()).toBe(true);
    expect(wrapper.find(".import-analysis-table").exists()).toBe(true);

    // Should show dataframe data in table
    const tableData = wrapper.vm.tableData;
    expect(tableData).toHaveLength(2);
    expect(tableData[0].reference).toBe("Smith2023");
    expect(tableData[0].title).toBe("A Study on Machine Learning");
  });

  it("shows loading state when loading prop is true", () => {
    const wrapper = mount(ImportAnalysisTable, createMountOptions({ loading: true }));

    expect(wrapper.find(".loading-state").exists()).toBe(true);
    expect(wrapper.text()).toContain("Loading...");
  });

  it("shows analyzing state when isAnalyzing is true", async () => {
    mockViewModel.isAnalyzing = true;

    const wrapper = mount(ImportAnalysisTable, createMountOptions());

    await wrapper.vm.$nextTick();

    expect(wrapper.find(".loading-state").exists()).toBe(true);
    expect(wrapper.text()).toContain("Analyzing import status...");
  });

  it("shows error state when hasError is true", async () => {
    mockViewModel.hasError = true;
    mockViewModel.errorMessage = "Test error message";

    const wrapper = mount(ImportAnalysisTable, createMountOptions());

    await wrapper.vm.$nextTick();

    expect(wrapper.find(".error-state").exists()).toBe(true);
    expect(wrapper.text()).toContain("Analysis Failed");
    expect(wrapper.text()).toContain("Test error message");
  });

  it("displays analysis summary correctly when analysis result is available", async () => {
    mockViewModel.analysisResult = mockAnalysisResult;

    const wrapper = mount(ImportAnalysisTable, createMountOptions());

    await wrapper.vm.$nextTick();

    const summaryStats = wrapper.find(".summary-stats");
    expect(summaryStats.exists()).toBe(true);

    expect(wrapper.text()).toContain("Total: 3");
    expect(wrapper.text()).toContain("Add: 1");
    expect(wrapper.text()).toContain("Update: 1");
    expect(wrapper.text()).toContain("Skip: 0");
    expect(wrapper.text()).toContain("Failed: 1");
  });

  it("displays default summary when no analysis result", () => {
    const wrapper = mount(ImportAnalysisTable, createMountOptions());

    const summaryData = wrapper.vm.summaryData;
    expect(summaryData.total_documents).toBe(2);
    expect(summaryData.add_count).toBe(2);
    expect(summaryData.update_count).toBe(0);
    expect(summaryData.skip_count).toBe(0);
    expect(summaryData.failed_count).toBe(0);
  });

  it("generates table data correctly from dataframe", () => {
    const wrapper = mount(ImportAnalysisTable, createMountOptions());

    const tableData = wrapper.vm.tableData;
    expect(tableData).toHaveLength(2);

    expect(tableData[0]).toMatchObject({
      reference: "Smith2023",
      title: "A Study on Machine Learning",
      authors: "John Smith, Jane Doe",
      year: "2023",
      files: "No files",
      status: "add",
      originalStatus: "add",
      canToggle: true,
    });

    expect(tableData[1]).toMatchObject({
      reference: "Brown2024",
      title: "Deep Learning Applications",
      authors: "Alice Brown",
      year: "2024",
      files: "No files",
      status: "add",
      originalStatus: "add",
      canToggle: true,
    });
  });

  it("generates table data correctly from analysis result", async () => {
    mockViewModel.analysisResult = mockAnalysisResult;

    const wrapper = mount(ImportAnalysisTable, createMountOptions());

    await wrapper.vm.$nextTick();

    const tableData = wrapper.vm.tableData;
    expect(tableData).toHaveLength(2); // Still 2 because dataframe has 2 rows

    // The table data should come from dataframe, not analysis result
    expect(tableData[0].reference).toBe("Smith2023");
    expect(tableData[0].title).toBe("A Study on Machine Learning");
  });

  it("generates table columns correctly", () => {
    const wrapper = mount(ImportAnalysisTable, createMountOptions());

    const columns = wrapper.vm.tableColumns;
    expect(columns.length).toBeGreaterThan(4); // At least reference, title, authors, year, files, status

    expect(columns[0]).toMatchObject({
      field: "reference",
      title: "Reference",
      width: 150,
      frozen: true,
    });

    // Find status column
    const statusColumn = columns.find(col => col.field === "status");
    expect(statusColumn).toMatchObject({
      field: "status",
      title: "Import Status",
      width: 150,
      frozen: true,
    });
  });

  it("calculates confirmed count correctly", async () => {
    const wrapper = mount(ImportAnalysisTable, createMountOptions());

    // Initially should count all documents as add
    expect(wrapper.vm.confirmedCount).toBe(2);

    // Change one document to ignore
    wrapper.vm.localDocumentActions = { Smith2023: "ignore" };
    expect(wrapper.vm.confirmedCount).toBe(1);
  });

  it("handles status toggle correctly", () => {
    const wrapper = mount(ImportAnalysisTable, createMountOptions());

    // Mock cell object
    const mockUpdate = jest.fn();
    const mockCell = {
      getValue: () => "add",
      getRow: () => ({
        getData: () => ({
          status: "add",
          originalStatus: "add",
          reference: "Smith2023",
          canToggle: true,
        }),
        update: mockUpdate,
      }),
    };

    // Test status toggle
    wrapper.vm.handleStatusClick({}, mockCell);

    expect(wrapper.vm.localDocumentActions["Smith2023"]).toBe("ignore");
    expect(mockUpdate).toHaveBeenCalledWith({ status: "ignore" });
  });

  it("emits update event when document actions change", () => {
    const wrapper = mount(ImportAnalysisTable, createMountOptions());

    wrapper.vm.emitUpdate();

    expect(wrapper.emitted("update")).toBeTruthy();
    const updateEvent = wrapper.emitted("update")[0][0];

    expect(updateEvent).toHaveProperty("confirmedDocuments");
    expect(updateEvent).toHaveProperty("totalConfirmed");
    expect(updateEvent).toHaveProperty("documentActions");
  });

  it("formats authors correctly", () => {
    const wrapper = mount(ImportAnalysisTable, createMountOptions());

    expect(wrapper.vm.formatAuthors(["Author 1", "Author 2"])).toBe("Author 1, Author 2");
    expect(wrapper.vm.formatAuthors("Single Author")).toBe("Single Author");
    expect(wrapper.vm.formatAuthors([])).toBe("N/A");
    expect(wrapper.vm.formatAuthors(null)).toBe("N/A");
  });

  it("formats files correctly", () => {
    const wrapper = mount(ImportAnalysisTable, createMountOptions());

    expect(wrapper.vm.formatFiles(["file1.pdf", "file2.pdf"])).toBe("file1.pdf, file2.pdf");
    expect(wrapper.vm.formatFiles([])).toBe("No files");
    expect(wrapper.vm.formatFiles(null)).toBe("No files");
  });

  it("determines toggle capability correctly", () => {
    const wrapper = mount(ImportAnalysisTable, createMountOptions());

    expect(wrapper.vm.canToggleStatus("add")).toBe(true);
    expect(wrapper.vm.canToggleStatus("update")).toBe(true);
    expect(wrapper.vm.canToggleStatus("ignore")).toBe(true);
    expect(wrapper.vm.canToggleStatus("skip")).toBe(false);
    expect(wrapper.vm.canToggleStatus("failed")).toBe(false);
  });

  it("resets local state correctly", () => {
    const wrapper = mount(ImportAnalysisTable, createMountOptions());

    // Set some state
    wrapper.vm.localDocumentActions = { Smith2023: "ignore" };

    // Reset local state
    wrapper.vm.resetLocalState();

    expect(wrapper.vm.localDocumentActions).toEqual({});
  });

  it("handles retry analysis", () => {
    const wrapper = mount(ImportAnalysisTable, createMountOptions());

    wrapper.vm.retryAnalysis();

    expect(mockViewModel.retryAnalysis).toHaveBeenCalled();
  });

  it("emits analysis-complete event when analysis result changes", async () => {
    const wrapper = mount(ImportAnalysisTable, createMountOptions());

    // Manually trigger the watch handler
    wrapper.vm.$options.watch.analysisResult.handler.call(wrapper.vm, mockAnalysisResult);

    expect(wrapper.emitted("analysis-complete")).toBeTruthy();
    expect(wrapper.emitted("analysis-complete")[0][0]).toBe(mockAnalysisResult);
  });
});
