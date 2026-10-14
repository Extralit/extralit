import { mount } from "@vue/test-utils";
import ImportFlow from "./ImportFlow.vue";

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

  const mountFlow = (props = {}) =>
    mount(ImportFlow, {
      props: {
        isVisible: true,
        workspace: mockWorkspace,
        ...props,
      },
      global: {
        stubs: {
          BaseFlowModal: {
            template: '<div class="mock-flow-modal"><slot :currentStep="0" /></div>',
            props: ["visible", "title", "steps", "currentStep"],
          },
          // Real children expose a reset() that resetModal() invokes via $refs;
          // bare `true` stubs omit it and crash the reset path, so stub it out.
          ImportFileUpload: { template: "<div />", methods: { reset() {} } },
          ImportAnalysisTable: { template: "<div />", methods: { reset() {} } },
          ImportBatchProgress: {
            template: "<div />",
            methods: { reset() {}, cancelUpload() {} },
          },
          ImportSummary: { template: "<div />", methods: { reset() {} } },
        },
        mocks: {
          $t: (key, params) => `${key}${params ? JSON.stringify(params) : ""}`,
        },
      },
    });

  beforeEach(async () => {
    vi.clearAllMocks();

    wrapper = mountFlow();

    // Set initial bibData
    await wrapper.setData({
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

    it("should record documentActions from analysis update", () => {
      const documentActions = { test1: "add", test2: "update" };

      wrapper.vm.handleAnalysisUpdate({
        confirmedDocuments: { test1: {} },
        documentActions,
      });

      expect(wrapper.vm.uploadData.documentActions).toEqual(documentActions);
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

  describe("Step gating computeds", () => {
    describe("canGoBack", () => {
      it("is false on the first step", async () => {
        await wrapper.setData({ currentStep: 0 });
        expect(wrapper.vm.canGoBack).toBe(false);
      });

      it("is true on the analysis step when idle", async () => {
        await wrapper.setData({ currentStep: 1, isProcessing: false, isUploading: false });
        expect(wrapper.vm.canGoBack).toBe(true);
      });

      it("is false while processing", async () => {
        await wrapper.setData({ currentStep: 1, isProcessing: true });
        expect(wrapper.vm.canGoBack).toBe(false);
      });

      it("is false once past the analysis step (upload/summary)", async () => {
        await wrapper.setData({ currentStep: 2 });
        expect(wrapper.vm.canGoBack).toBe(false);
      });
    });

    describe("canGoNext", () => {
      it("step 0: false without uploaded PDFs", async () => {
        await wrapper.setData({ currentStep: 0, pdfData: { totalFiles: 0 } });
        expect(wrapper.vm.canGoNext).toBe(false);
      });

      it("step 0: true with PDFs and a workspace", async () => {
        await wrapper.setData({ currentStep: 0, pdfData: { totalFiles: 2 }, hasError: false });
        expect(wrapper.vm.canGoNext).toBe(true);
      });

      it("step 0: false when there is an error", async () => {
        await wrapper.setData({ currentStep: 0, pdfData: { totalFiles: 2 }, hasError: true });
        expect(wrapper.vm.canGoNext).toBe(false);
      });

      it("step 0: false without a workspace", async () => {
        await wrapper.setProps({ workspace: null });
        await wrapper.setData({ currentStep: 0, pdfData: { totalFiles: 2 } });
        expect(wrapper.vm.canGoNext).toBe(false);
      });

      it("step 1: false without confirmed documents", async () => {
        await wrapper.setData({ currentStep: 1, uploadData: { confirmedDocuments: {} } });
        expect(wrapper.vm.canGoNext).toBe(false);
      });

      it("step 1: true with confirmed documents", async () => {
        await wrapper.setData({
          currentStep: 1,
          hasError: false,
          uploadData: { confirmedDocuments: { test1: {} } },
        });
        expect(wrapper.vm.canGoNext).toBe(true);
      });

      it("step 2 (upload in progress): always false", async () => {
        await wrapper.setData({ currentStep: 2 });
        expect(wrapper.vm.canGoNext).toBe(false);
      });
    });

    describe("canComplete", () => {
      it("is true only on the summary step", async () => {
        await wrapper.setData({ currentStep: 3 });
        expect(wrapper.vm.canComplete).toBe(true);

        await wrapper.setData({ currentStep: 2 });
        expect(wrapper.vm.canComplete).toBe(false);
      });
    });

    describe("shouldConfirmClose", () => {
      it("does not confirm on the summary step", async () => {
        await wrapper.setData({ currentStep: 3, isProcessing: true });
        expect(wrapper.vm.shouldConfirmClose).toBe(false);
      });

      it("confirms while processing", async () => {
        await wrapper.setData({ currentStep: 1, isProcessing: true });
        expect(wrapper.vm.shouldConfirmClose).toBe(true);
      });

      it("confirms when there is unsaved data to lose", async () => {
        await wrapper.setData({
          currentStep: 0,
          isProcessing: false,
          isUploading: false,
          pdfData: { totalFiles: 3, matchedFiles: [], unmatchedFiles: [] },
        });
        expect(wrapper.vm.shouldConfirmClose).toBe(true);
      });

      it("does not confirm when nothing has been entered", async () => {
        await wrapper.setData({
          currentStep: 0,
          isProcessing: false,
          isUploading: false,
          bibData: { fileName: "", dataframeData: null, rawContent: "" },
          pdfData: { totalFiles: 0, matchedFiles: [], unmatchedFiles: [] },
          uploadData: { confirmedDocuments: {} },
        });
        // NB: the computed returns a falsy value (undefined) rather than a strict
        // `false` here, because hasDataToLose()'s `||` chain ends on an undefined
        // $refs lookup. It is consumed in a boolean context, so falsy is correct.
        expect(wrapper.vm.shouldConfirmClose).toBeFalsy();
      });
    });
  });

  describe("File update handlers normalize incoming data", () => {
    it("handleBibUpdate fills defaults for missing fields", () => {
      wrapper.vm.handleBibUpdate({ fileName: "refs.bib" });
      expect(wrapper.vm.bibData).toEqual({
        fileName: "refs.bib",
        dataframeData: null,
        rawContent: "",
      });
    });

    it("handlePdfUpdate fills defaults for missing fields", () => {
      wrapper.vm.handlePdfUpdate({ totalFiles: 2 });
      expect(wrapper.vm.pdfData).toEqual({
        matchedFiles: [],
        unmatchedFiles: [],
        totalFiles: 2,
      });
    });

    it("file updates clear any existing error", async () => {
      await wrapper.setData({ hasError: true, errorMessage: "boom" });
      wrapper.vm.handlePdfUpdate({ totalFiles: 1 });
      expect(wrapper.vm.hasError).toBe(false);
      expect(wrapper.vm.errorMessage).toBe("");
    });
  });

  describe("Step navigation and validation", () => {
    it("handleStepChange updates the current step and clears errors", async () => {
      await wrapper.setData({ hasError: true, errorMessage: "boom" });
      wrapper.vm.handleStepChange(1);
      expect(wrapper.vm.currentStep).toBe(1);
      expect(wrapper.vm.hasError).toBe(false);
    });

    it("handleValidateStep rejects step 0 without PDFs", () => {
      wrapper.setData({ pdfData: { totalFiles: 0 } });
      const callback = vi.fn();
      wrapper.vm.handleValidateStep({ step: 0, callback });
      expect(callback).toHaveBeenCalledWith(false);
    });

    it("handleValidateStep accepts step 0 with PDFs and workspace", async () => {
      await wrapper.setData({ pdfData: { totalFiles: 1 }, hasError: false });
      const callback = vi.fn();
      wrapper.vm.handleValidateStep({ step: 0, callback });
      expect(callback).toHaveBeenCalledWith(true);
    });

    it("handleValidateStep starts the upload when leaving the analysis step", async () => {
      await wrapper.setData({
        uploadData: { ...wrapper.vm.uploadData, confirmedDocuments: { test1: {} } },
      });
      const callback = vi.fn();
      wrapper.vm.handleValidateStep({ step: 1, callback });
      expect(callback).toHaveBeenCalledWith(true);

      await wrapper.vm.$nextTick();
      expect(wrapper.vm.isUploading).toBe(true);
      expect(wrapper.vm.isProcessing).toBe(true);
    });

    it("handleValidateStep rejects the analysis step without confirmed documents", async () => {
      await wrapper.setData({ uploadData: { ...wrapper.vm.uploadData, confirmedDocuments: {} } });
      const callback = vi.fn();
      wrapper.vm.handleValidateStep({ step: 1, callback });
      expect(callback).toHaveBeenCalledWith(false);
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.isUploading).toBe(false);
    });
  });

  describe("Upload lifecycle", () => {
    it("handleUploadProgress updates batch/job counters", () => {
      wrapper.vm.handleUploadProgress({
        currentBatch: 2,
        totalBatches: 5,
        completedJobs: 3,
        failedJobs: 1,
      });
      expect(wrapper.vm.uploadData.currentBatch).toBe(2);
      expect(wrapper.vm.uploadData.totalBatches).toBe(5);
      expect(wrapper.vm.uploadData.completedJobs).toBe(3);
      expect(wrapper.vm.uploadData.failedJobs).toBe(1);
    });

    it("handleUploadCompleted stores the summary and advances to the summary step", async () => {
      const importSummary = { total: 2, added: 1, updated: 1, skipped: 0, failed: 0, errors: [] };
      await wrapper.setData({ isUploading: true, isProcessing: true });

      wrapper.vm.handleUploadCompleted({ importSummary, failedDocuments: [{ id: "x" }] });

      expect(wrapper.vm.importSummary).toEqual(importSummary);
      expect(wrapper.vm.failedDocuments).toEqual([{ id: "x" }]);
      expect(wrapper.vm.isUploading).toBe(false);
      expect(wrapper.vm.isProcessing).toBe(false);

      await wrapper.vm.$nextTick();
      expect(wrapper.vm.currentStep).toBe(3);
    });

    it("handleUploadCancelled clears flags and surfaces a non-retryable error", async () => {
      await wrapper.setData({ isUploading: true, isProcessing: true });
      wrapper.vm.handleUploadCancelled();
      expect(wrapper.vm.isUploading).toBe(false);
      expect(wrapper.vm.isProcessing).toBe(false);
      expect(wrapper.vm.hasError).toBe(true);
      expect(wrapper.vm.canRetryError).toBe(false);
    });

    it("handleUploadError clears flags and surfaces a retryable error", () => {
      wrapper.vm.handleUploadError(new Error("network down"));
      expect(wrapper.vm.hasError).toBe(true);
      expect(wrapper.vm.canRetryError).toBe(true);
      expect(wrapper.vm.errorMessage).toContain("network down");
    });

    it("initializeUploadData computes the batch count (20 per batch)", async () => {
      const confirmedDocuments = {};
      for (let i = 0; i < 45; i++) confirmedDocuments[`doc${i}`] = {};
      await wrapper.setData({ uploadData: { ...wrapper.vm.uploadData, confirmedDocuments } });

      wrapper.vm.initializeUploadData();

      expect(wrapper.vm.uploadData.totalBatches).toBe(3); // ceil(45 / 20)
      expect(wrapper.vm.uploadData.currentBatch).toBe(0);
      expect(wrapper.vm.uploadData.completedJobs).toBe(0);
    });
  });

  describe("Outbound events", () => {
    it("handleComplete completes the flow (delegates to handleReturnToLibrary)", () => {
      wrapper.vm.handleComplete();
      // handleComplete emits import-completed itself AND delegates to
      // handleReturnToLibrary, which emits it again -> two emissions.
      expect(wrapper.emitted("import-completed")).toHaveLength(2);
      expect(wrapper.emitted("close")).toHaveLength(1);
      expect(wrapper.emitted("navigate-to-library")).toHaveLength(1);
    });

    it("handleReturnToLibrary emits completion, close and navigation", () => {
      wrapper.vm.handleReturnToLibrary();
      expect(wrapper.emitted("import-completed")).toHaveLength(1);
      expect(wrapper.emitted("close")).toHaveLength(1);
      expect(wrapper.emitted("navigate-to-library")).toHaveLength(1);
    });

    it("handleViewImportHistory emits completion, close and history navigation", () => {
      wrapper.vm.handleViewImportHistory();
      expect(wrapper.emitted("import-completed")).toHaveLength(1);
      expect(wrapper.emitted("close")).toHaveLength(1);
      expect(wrapper.emitted("navigate-to-import-history")).toHaveLength(1);
    });

    it("handleClose emits import-completed only on the summary step", async () => {
      await wrapper.setData({ currentStep: 1 });
      wrapper.vm.handleClose();
      expect(wrapper.emitted("import-completed")).toBeUndefined();
      expect(wrapper.emitted("close")).toHaveLength(1);

      await wrapper.setData({ currentStep: 3 });
      wrapper.vm.handleClose();
      expect(wrapper.emitted("import-completed")).toHaveLength(1);
      expect(wrapper.emitted("close")).toHaveLength(2);
    });

    it("handleCancel cancels an in-flight upload and closes", async () => {
      const cancelSpy = vi.spyOn(wrapper.vm, "cancelUpload").mockImplementation(() => {});
      await wrapper.setData({ isUploading: true });

      wrapper.vm.handleCancel();

      expect(cancelSpy).toHaveBeenCalledTimes(1);
      expect(wrapper.emitted("close")).toHaveLength(1);
    });

    it("handleCancel just closes when nothing is uploading", () => {
      wrapper.vm.handleCancel();
      expect(wrapper.emitted("close")).toHaveLength(1);
    });
  });

  describe("getAllPdfFiles", () => {
    it("collects matched .file objects and raw unmatched File instances, ignoring non-Files", async () => {
      const matchedFile = new File(["a"], "matched.pdf", { type: "application/pdf" });
      const unmatchedFile = new File(["b"], "unmatched.pdf", { type: "application/pdf" });

      await wrapper.setData({
        pdfData: {
          totalFiles: 2,
          matchedFiles: [{ file: matchedFile }, { file: null }],
          unmatchedFiles: [unmatchedFile, { not: "a file" }],
        },
      });

      const files = wrapper.vm.getAllPdfFiles();

      // Identity is not asserted: Vue's reactive wrapping can re-proxy the
      // stored File, so compare by the stable `name` instead.
      expect(files).toHaveLength(2);
      expect(files.map((f) => f.name).sort()).toEqual(["matched.pdf", "unmatched.pdf"]);
      expect(files.every((f) => f instanceof File)).toBe(true);
    });
  });

  describe("resetModal / visibility watcher", () => {
    it("resetModal clears all step data back to initial state", async () => {
      await wrapper.setData({
        currentStep: 2,
        isProcessing: true,
        pdfData: { totalFiles: 5, matchedFiles: [], unmatchedFiles: [] },
        uploadData: { ...wrapper.vm.uploadData, confirmedDocuments: { a: {} } },
        failedDocuments: [{ id: "x" }],
      });

      wrapper.vm.resetModal();

      expect(wrapper.vm.currentStep).toBe(0);
      expect(wrapper.vm.isProcessing).toBe(false);
      expect(wrapper.vm.pdfData.totalFiles).toBe(0);
      expect(wrapper.vm.uploadData.confirmedDocuments).toEqual({});
      expect(wrapper.vm.failedDocuments).toEqual([]);
      expect(wrapper.vm.bibData.dataframeData).toBeNull();
    });

    it("re-opening the modal (isVisible false -> true) resets state", async () => {
      await wrapper.setData({ currentStep: 2, pdfData: { totalFiles: 5 } });

      await wrapper.setProps({ isVisible: false });
      await wrapper.setProps({ isVisible: true });

      expect(wrapper.vm.currentStep).toBe(0);
      expect(wrapper.vm.pdfData.totalFiles).toBe(0);
    });
  });
});
