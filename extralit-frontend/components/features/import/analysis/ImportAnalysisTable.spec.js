import { mount } from "@vue/test-utils";
import ImportAnalysisTable from "./ImportAnalysisTable.vue";
import { useImportAnalysisTableViewModel } from "./useImportAnalysisTableViewModel";

// Mock dependencies inline to avoid hoisting issues
vi.mock("ts-injecty", () => ({
  useResolve: vi.fn(() => mockUseCase),
}));

vi.mock("./useImportAnalysisTableViewModel", () => ({
  useImportAnalysisTableViewModel: vi.fn(() => ({
    isAnalyzing: false,
    hasError: false,
    errorMessage: "",
    analysisResult: null,
    documentActions: {},
    reset: vi.fn(),
    analyzeImport: vi.fn(),
    retryAnalysis: vi.fn(),
  })),
}));

const mockUseCase = {
  analyzeImport: vi.fn(),
};

describe("ImportAnalysisTable", () => {
  let wrapper;

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
        reference: "test1",
        title: "Test Paper 1",
        authors: "Author 1",
        year: "2023",
        filePaths: ["test1.pdf"],
      },
      {
        reference: "test2",
        title: "Test Paper 2",
        authors: "Author 2",
        year: "2024",
        filePaths: [], // No PDFs
      },
    ],
  };

  const mockWorkspace = {
    id: "workspace-1",
    name: "Test Workspace",
  };

  beforeEach(() => {
    vi.clearAllMocks();

    wrapper = mount(ImportAnalysisTable, {
      props: {
        dataframeData: mockDataframeData,
        pdfData: { matchedFiles: [] },
        workspace: mockWorkspace,
        loading: false,
      },
      global: { stubs: {
        BaseSpinner: true,
        BaseIcon: true,
        BaseButton: true,
        BaseSimpleTable: {
          template: '<div class="mock-simple-table"></div>',
          props: ["data", "columns", "options"],
        },
      } },
    });
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
    vi.restoreAllMocks();
  });

  describe("Basic Rendering", () => {
    it("should render the analysis table", () => {
      expect(wrapper.find(".import-analysis-table").exists()).toBe(true);
    });

    it("should show summary statistics", () => {
      const summaryStats = wrapper.find(".summary-stats");
      expect(summaryStats.exists()).toBe(true);
    });

    it("should display references with and without PDFs count", () => {
      expect(wrapper.vm.referencesWithoutPdfsCount).toBe(1); // test2 has no PDFs
      expect(wrapper.vm.referencesWithPdfsCount).toBe(1); // test1 has PDFs
    });
  });

  describe("Table Data Filtering", () => {
    it("should only show references with PDFs in table data", () => {
      // Only test1 has PDFs, so only it should be shown
      expect(wrapper.vm.tableData.length).toBe(1);
      expect(wrapper.vm.tableData[0].reference).toBe("test1");
    });

    it("should filter dataframe data to only include references with PDFs", () => {
      const filtered = wrapper.vm.filteredDataframeData;
      expect(filtered.data.length).toBe(1);
      expect(filtered.data[0].reference).toBe("test1");
    });
  });

  describe("Confirmed Count Calculation", () => {
    it("should only count references with PDFs", () => {
      // Only test1 has PDFs, so only it should be counted
      expect(wrapper.vm.confirmedCount).toBe(1);
    });
  });

  describe("Emit Update", () => {
    it("should emit update with correct data structure", () => {
      wrapper.vm.emitUpdate();

      const updateEvents = wrapper.emitted("update");
      expect(updateEvents).toBeTruthy();
      expect(updateEvents[updateEvents.length - 1][0]).toEqual(
        expect.objectContaining({
          confirmedDocuments: expect.any(Object),
          totalConfirmed: expect.any(Number),
          documentActions: expect.any(Object),
          filteredDataframeData: expect.any(Object),
        })
      );
    });

    it("should only include references with PDFs in confirmed documents", () => {
      wrapper.vm.emitUpdate();

      const updateEvents = wrapper.emitted("update");
      const emittedData = updateEvents[updateEvents.length - 1][0];
      expect(Object.keys(emittedData.confirmedDocuments)).toEqual(["test1"]);
      expect(emittedData.totalConfirmed).toBe(1);
      expect(emittedData.filteredDataframeData.data.length).toBe(1);
      expect(emittedData.filteredDataframeData.data[0].reference).toBe("test1");
    });
  });

  describe("Reset Local State", () => {
    it("should reset local document actions when resetting local state", () => {
      wrapper.vm.resetLocalState();

      expect(wrapper.vm.localDocumentActions).toEqual({});
    });
  });

  describe("Loading and Error States", () => {
    it("should show loading state when loading prop is true", () => {
      wrapper = mount(ImportAnalysisTable, {
        props: {
          dataframeData: mockDataframeData,
          pdfData: { matchedFiles: [] },
          workspace: mockWorkspace,
          loading: true,
        },
        global: { stubs: {
          BaseSpinner: true,
          BaseIcon: true,
          BaseButton: true,
          BaseSimpleTable: true,
        } },
      });

      expect(wrapper.find(".loading-state").exists()).toBe(true);
    });

    it("should show error state when hasError is true", () => {
      useImportAnalysisTableViewModel.mockReturnValue({
        isAnalyzing: false,
        hasError: true,
        errorMessage: "Test error",
        analysisResult: null,
        documentActions: {},
        reset: vi.fn(),
        analyzeImport: vi.fn(),
        retryAnalysis: vi.fn(),
      });

      wrapper = mount(ImportAnalysisTable, {
        props: {
          dataframeData: mockDataframeData,
          pdfData: { matchedFiles: [] },
          workspace: mockWorkspace,
          loading: false,
        },
        global: { stubs: {
          BaseSpinner: true,
          BaseIcon: true,
          BaseButton: true,
          BaseSimpleTable: true,
        } },
      });

      expect(wrapper.find(".error-state").exists()).toBe(true);
      expect(wrapper.text()).toContain("Test error");
    });
  });
});
