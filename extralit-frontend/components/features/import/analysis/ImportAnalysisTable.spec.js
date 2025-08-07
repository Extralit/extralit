import { mount } from "@vue/test-utils";
import ImportAnalysisTable from "./ImportAnalysisTable.vue";

// Mock dependencies inline to avoid hoisting issues
jest.mock("ts-injecty", () => ({
  useResolve: jest.fn(() => mockUseCase),
}));

jest.mock("@nuxtjs/composition-api", () => ({
  ref: jest.fn(),
  watch: jest.fn(),
}));

jest.mock("./useImportAnalysisTableViewModel", () => ({
  useImportAnalysisTableViewModel: jest.fn(() => ({
    isAnalyzing: false,
    hasError: false,
    errorMessage: "",
    analysisResult: null,
    documentActions: {},
    reset: jest.fn(),
    analyzeImport: jest.fn(),
    retryAnalysis: jest.fn(),
  })),
}));

const mockUseCase = {
  analyzeImport: jest.fn(),
};

describe("ImportAnalysisTable", () => {
  let wrapper;
  let mockRef;
  let mockWatch;

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
    jest.clearAllMocks();

    const compositionApi = require("@nuxtjs/composition-api");
    mockRef = compositionApi.ref;
    mockWatch = compositionApi.watch;

    // Configure mock behavior
    mockRef.mockImplementation((initialValue) => ({
      value: initialValue,
    }));

    mockWatch.mockImplementation(() => {});

    wrapper = mount(ImportAnalysisTable, {
      propsData: {
        dataframeData: mockDataframeData,
        pdfData: { matchedFiles: [] },
        workspace: mockWorkspace,
        loading: false,
      },
      stubs: {
        BaseSpinner: true,
        BaseIcon: true,
        BaseButton: true,
        BaseRadioButton: {
          template: '<input type="radio" class="mock-radio-button" />',
          props: ["value", "name"],
          model: {
            prop: "modelValue",
            event: "change",
          },
        },
        BaseSimpleTable: {
          template: '<div class="mock-simple-table"></div>',
          props: ["data", "columns", "options"],
        },
      },
    });
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.destroy();
    }
    jest.restoreAllMocks();
  });

  describe("Import Mode Toggle", () => {
    it("should render import mode options", () => {
      const importOptions = wrapper.find(".import-options");
      expect(importOptions.exists()).toBe(true);

      const radioButtons = wrapper.findAll(".mock-radio-button");
      expect(radioButtons.length).toBe(2);
    });

    it("should default to 'all' import mode", () => {
      expect(wrapper.vm.importMode).toBe("all");
    });

    it("should calculate references with and without PDFs correctly", () => {
      expect(wrapper.vm.referencesWithoutPdfsCount).toBe(1); // test2 has no PDFs
      expect(wrapper.vm.referencesWithPdfsCount).toBe(1); // test1 has PDFs
    });

    it("should filter table data based on import mode", () => {
      // Default mode 'all' should show all references
      expect(wrapper.vm.tableData.length).toBe(2);

      // Switch to 'with-pdfs' mode
      wrapper.setData({ importMode: "with-pdfs" });
      expect(wrapper.vm.tableData.length).toBe(1);
      expect(wrapper.vm.tableData[0].reference).toBe("test1");
    });

    it("should handle import mode change correctly", () => {
      const emitSpy = jest.spyOn(wrapper.vm, "$emit");

      // Switch to 'with-pdfs' mode
      wrapper.setData({ importMode: "with-pdfs" });
      wrapper.vm.handleImportModeChange();

      // Should set references without PDFs to ignore
      expect(wrapper.vm.localDocumentActions.test2).toBe("ignore");
      expect(emitSpy).toHaveBeenCalledWith("update", expect.any(Object));
    });

    it("should restore original status when switching back to 'all' mode", () => {
      // First switch to 'with-pdfs' mode
      wrapper.setData({ importMode: "with-pdfs" });
      wrapper.vm.handleImportModeChange();
      expect(wrapper.vm.localDocumentActions.test2).toBe("ignore");

      // Switch back to 'all' mode
      wrapper.setData({ importMode: "all" });
      wrapper.vm.handleImportModeChange();

      // Should remove the ignore action
      expect(wrapper.vm.localDocumentActions.test2).toBeUndefined();
    });
  });

  describe("Confirmed Count Calculation", () => {
    it("should respect import mode when calculating confirmed count", () => {
      // In 'all' mode, both references should be counted (default to 'add')
      expect(wrapper.vm.confirmedCount).toBe(2);

      // Switch to 'with-pdfs' mode
      wrapper.setData({ importMode: "with-pdfs" });
      expect(wrapper.vm.confirmedCount).toBe(1); // Only test1 has PDFs
    });
  });

  describe("Filtered Dataframe Data", () => {
    it("should return original dataframe data when import mode is 'all'", () => {
      expect(wrapper.vm.filteredDataframeData).toEqual(mockDataframeData);
    });

    it("should filter out references without PDFs when import mode is 'with-pdfs'", () => {
      wrapper.setData({ importMode: "with-pdfs" });

      const filtered = wrapper.vm.filteredDataframeData;
      expect(filtered.data.length).toBe(1);
      expect(filtered.data[0].reference).toBe("test1");
    });
  });

  describe("Emit Update", () => {
    it("should include import mode and filtered dataframe data in emitted update data", () => {
      const emitSpy = jest.spyOn(wrapper.vm, "$emit");

      wrapper.vm.emitUpdate();

      expect(emitSpy).toHaveBeenCalledWith(
        "update",
        expect.objectContaining({
          importMode: "all",
          confirmedDocuments: expect.any(Object),
          totalConfirmed: expect.any(Number),
          documentActions: expect.any(Object),
          filteredDataframeData: expect.any(Object),
        })
      );
    });

    it("should exclude references without PDFs when import mode is 'with-pdfs'", () => {
      const emitSpy = jest.spyOn(wrapper.vm, "$emit");

      wrapper.setData({ importMode: "with-pdfs" });
      wrapper.vm.emitUpdate();

      const emittedData = emitSpy.mock.calls[0][1];
      expect(Object.keys(emittedData.confirmedDocuments)).toEqual(["test1"]);
      expect(emittedData.totalConfirmed).toBe(1);
      expect(emittedData.filteredDataframeData.data.length).toBe(1);
      expect(emittedData.filteredDataframeData.data[0].reference).toBe("test1");
    });
  });

  describe("Reset Local State", () => {
    it("should reset import mode to 'all' when resetting local state", () => {
      wrapper.setData({ importMode: "with-pdfs" });
      wrapper.vm.resetLocalState();

      expect(wrapper.vm.importMode).toBe("all");
      expect(wrapper.vm.localDocumentActions).toEqual({});
    });
  });
});
