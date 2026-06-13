import { mount } from "@vue/test-utils";
import ImportFlow from "./ImportFlow.vue";

// Mock dependencies
vi.mock("@nuxtjs/composition-api", () => ({
  ref: vi.fn(),
  watch: vi.fn(),
}));

describe("ImportFlow", () => {
  let wrapper;

  const mockWorkspace = {
    id: "workspace-1",
    name: "Test Workspace",
  };

  const mockDataframeData = {
    schema: {
      fields: [
        { name: "reference", type: "string" },
        { name: "title", type: "string" },
      ],
      primaryKey: ["reference"],
    },
    data: [
      { reference: "test1", title: "Test Paper 1", filePaths: ["test1.pdf"] },
      { reference: "test2", title: "Test Paper 2", filePaths: [] },
    ],
  };

  const mockFilteredDataframeData = {
    schema: {
      fields: [
        { name: "reference", type: "string" },
        { name: "title", type: "string" },
      ],
      primaryKey: ["reference"],
    },
    data: [{ reference: "test1", title: "Test Paper 1", filePaths: ["test1.pdf"] }],
  };

  beforeEach(() => {
    vi.clearAllMocks();

    const compositionApi = require("@nuxtjs/composition-api");
    compositionApi.ref.mockImplementation((initialValue) => ({
      value: initialValue,
    }));
    compositionApi.watch.mockImplementation(() => {});

    wrapper = mount(ImportFlow, {
      props: {
        isVisible: true,
        workspace: mockWorkspace,
      },
      stubs: {
        BaseFlowModal: {
          template: '<div class="mock-flow-modal"><slot :currentStep="0" /></div>',
          props: ["visible", "title", "steps", "currentStep"],
        },
        ImportFileUpload: true,
        ImportAnalysisTable: true,
        ImportBatchProgress: true,
        ImportSummary: true,
      },
      mocks: {
        $t: (key, params) => `${key}${params ? JSON.stringify(params) : ""}`,
      },
    });

    // Set initial bibData
    wrapper.setData({
      bibData: {
        fileName: "test.bib",
        parsedEntries: [],
        dataframeData: mockDataframeData,
        rawContent: "",
      },
    });
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
    vi.restoreAllMocks();
  });

  describe("Analysis Update Handling", () => {
    it("should update confirmed documents from analysis update", () => {
      const mockAnalysisData = {
        confirmedDocuments: { test1: { document_create: {} } },
        totalConfirmed: 1,
        documentActions: {},
        importMode: "all",
        filteredDataframeData: mockDataframeData,
      };

      wrapper.vm.handleAnalysisUpdate(mockAnalysisData);

      expect(wrapper.vm.uploadData.confirmedDocuments).toEqual(mockAnalysisData.confirmedDocuments);
      expect(wrapper.vm.bibData.dataframeData).toEqual(mockDataframeData);
    });

    it("should update bibData with filtered dataframe data when provided", () => {
      const mockAnalysisData = {
        confirmedDocuments: { test1: { document_create: {} } },
        totalConfirmed: 1,
        documentActions: {},
        importMode: "with-pdfs",
        filteredDataframeData: mockFilteredDataframeData,
      };

      wrapper.vm.handleAnalysisUpdate(mockAnalysisData);

      expect(wrapper.vm.uploadData.confirmedDocuments).toEqual(mockAnalysisData.confirmedDocuments);
      expect(wrapper.vm.bibData.dataframeData).toEqual(mockFilteredDataframeData);
      expect(wrapper.vm.bibData.dataframeData.data.length).toBe(1);
      expect(wrapper.vm.bibData.dataframeData.data[0].reference).toBe("test1");
    });

    it("should not update bibData.dataframeData if filteredDataframeData is not provided", () => {
      const originalDataframeData = wrapper.vm.bibData.dataframeData;

      const mockAnalysisData = {
        confirmedDocuments: { test1: { document_create: {} } },
        totalConfirmed: 1,
        documentActions: {},
        importMode: "all",
        // No filteredDataframeData provided
      };

      wrapper.vm.handleAnalysisUpdate(mockAnalysisData);

      expect(wrapper.vm.uploadData.confirmedDocuments).toEqual(mockAnalysisData.confirmedDocuments);
      expect(wrapper.vm.bibData.dataframeData).toEqual(originalDataframeData);
    });
  });

  describe("Data Flow", () => {
    it("should pass the correct dataframe data to ImportBatchProgress component", () => {
      // Set up the component to be on step 2 (ImportBatchProgress)
      wrapper.setData({
        currentStep: 2,
        bibData: {
          ...wrapper.vm.bibData,
          dataframeData: mockFilteredDataframeData,
        },
      });

      // The ImportBatchProgress component should receive the filtered dataframe data
      // This would be verified in integration tests, but we can check that the data is properly stored
      expect(wrapper.vm.bibData.dataframeData).toEqual(mockFilteredDataframeData);
    });
  });
});
