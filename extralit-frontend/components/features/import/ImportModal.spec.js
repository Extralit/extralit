import { mount } from "@vue/test-utils";
import ImportModal from "./ImportModal.vue";

describe("ImportModal", () => {
  let wrapper;

  beforeEach(() => {
    wrapper = mount(ImportModal, {
      propsData: {
        isVisible: true,
      },
      stubs: {
        BaseFlowModal: true,
        BaseButton: true,
        BaseIcon: true,
        ImportFileUpload: true,
        ImportAnalysisTable: true,
        ImportBatchProgress: true,
        ImportSummary: true,
        svgicon: true,
      },
    });
  });

  afterEach(() => {
    wrapper.destroy();
  });

  describe("Modal State Management", () => {
    it("should initialize with correct default state", () => {
      expect(wrapper.vm.currentStep).toBe(0);
      expect(wrapper.vm.totalSteps).toBe(4);
      expect(wrapper.vm.isProcessing).toBe(false);
      expect(wrapper.vm.isAnalyzing).toBe(false);
      expect(wrapper.vm.isUploading).toBe(false);
      expect(wrapper.vm.hasError).toBe(false);
    });

    it("should reset modal state when isVisible changes to true", async () => {
      wrapper.vm.currentStep = 3;
      wrapper.vm.hasError = true;
      wrapper.vm.errorMessage = "Test error";

      await wrapper.setProps({ isVisible: false });
      await wrapper.setProps({ isVisible: true });

      expect(wrapper.vm.currentStep).toBe(0);
      expect(wrapper.vm.hasError).toBe(false);
      expect(wrapper.vm.errorMessage).toBe("");
    });
  });

  describe("Step Navigation", () => {
    it("should handle step changes correctly", () => {
      wrapper.vm.handleStepChange(2);
      expect(wrapper.vm.currentStep).toBe(2);
    });
  });

  describe("Step Data Handlers", () => {
    it("should handle BibTeX file update event", () => {
      const mockData = {
        fileName: "test.bib",
        parsedEntries: [{ reference: "test" }],
        dataframeData: { schema: {}, data: [] },
        rawContent: "mock content",
      };

      wrapper.vm.handleBibUpdate(mockData);

      expect(wrapper.vm.bibData).toEqual(mockData);
      expect(wrapper.vm.hasError).toBe(false);
    });

    it("should handle PDF files update event", () => {
      const mockData = {
        matchedFiles: [{ filename: "test.pdf" }],
        unmatchedFiles: [],
        totalFiles: 1,
      };

      wrapper.vm.handlePdfUpdate(mockData);

      expect(wrapper.vm.pdfData).toEqual(mockData);
      expect(wrapper.vm.hasError).toBe(false);
    });

    it("should handle analysis update event", () => {
      const mockDocuments = { test: { action: "add" } };

      wrapper.vm.handleAnalysisUpdate({ confirmedDocuments: mockDocuments });

      expect(wrapper.vm.uploadData.confirmedDocuments).toEqual(mockDocuments);
      expect(wrapper.vm.hasError).toBe(false);
    });

    it("should handle upload completed event", () => {
      const mockSummary = {
        totalProcessed: 10,
        successfullyAdded: 8,
        updated: 1,
        skipped: 1,
        failed: 0,
        errors: [],
        importId: "test-import-123",
      };

      wrapper.vm.handleUploadCompleted(mockSummary);

      expect(wrapper.vm.summaryData).toEqual(mockSummary);
      expect(wrapper.vm.isUploading).toBe(false);
      expect(wrapper.vm.isProcessing).toBe(false);
    });
  });

  describe("Error Handling", () => {
    it("should show error with retry option", () => {
      wrapper.vm.showError("Test error message", true);

      expect(wrapper.vm.hasError).toBe(true);
      expect(wrapper.vm.errorMessage).toBe("Test error message");
      expect(wrapper.vm.canRetryError).toBe(true);
    });

    it("should clear error state", () => {
      wrapper.vm.hasError = true;
      wrapper.vm.errorMessage = "Test error";
      wrapper.vm.canRetryError = true;

      wrapper.vm.clearError();

      expect(wrapper.vm.hasError).toBe(false);
      expect(wrapper.vm.errorMessage).toBe("");
      expect(wrapper.vm.canRetryError).toBe(false);
    });

    it("should handle validation errors", () => {
      const mockError = { message: "Validation failed" };

      wrapper.vm.handleValidationError(mockError);

      expect(wrapper.vm.hasError).toBe(true);
      expect(wrapper.vm.errorMessage).toBe("Validation failed");
      expect(wrapper.vm.canRetryError).toBe(true);
    });
  });

  describe("Modal Lifecycle", () => {
    it("should emit close event when handleClose is called", () => {
      wrapper.vm.handleClose();

      expect(wrapper.emitted("close")).toBeTruthy();
    });

    it("should emit navigation events", () => {
      wrapper.vm.handleReturnToLibrary();
      expect(wrapper.emitted("navigate-to-library")).toBeTruthy();

      wrapper.vm.handleViewImportHistory();
      expect(wrapper.emitted("navigate-to-import-history")).toBeTruthy();
    });

    it("should reset all data when resetModal is called", () => {
      // Set some state
      wrapper.vm.currentStep = 3;
      wrapper.vm.hasError = true;
      wrapper.vm.bibData.parsedEntries = [{ test: "data" }];

      wrapper.vm.resetModal();

      expect(wrapper.vm.currentStep).toBe(0);
      expect(wrapper.vm.hasError).toBe(false);
      expect(wrapper.vm.bibData.parsedEntries).toEqual([]);
    });
  });

  describe("Step Definitions", () => {
    it("should have correct step definitions", () => {
      expect(wrapper.vm.steps).toHaveLength(4);
      expect(wrapper.vm.steps[0].id).toBe("file-upload");
      expect(wrapper.vm.steps[1].id).toBe("analysis");
      expect(wrapper.vm.steps[2].id).toBe("progress");
      expect(wrapper.vm.steps[3].id).toBe("summary");
    });
  });

  describe("Confirm Close Behavior", () => {
    it("should require confirmation during import process", () => {
      wrapper.vm.currentStep = 1;
      wrapper.vm.isProcessing = true;
      wrapper.vm.bibData.parsedEntries = [{ reference: "test" }];

      expect(wrapper.vm.shouldConfirmClose).toBe(true);
    });

    it("should not require confirmation after successful completion", () => {
      wrapper.vm.currentStep = 3; // Summary step
      wrapper.vm.isProcessing = false;
      wrapper.vm.isUploading = false;

      expect(wrapper.vm.shouldConfirmClose).toBe(false);
    });

    it("should require confirmation when user has data to lose", () => {
      wrapper.vm.currentStep = 0;
      wrapper.vm.bibData.parsedEntries = [{ reference: "test" }];

      expect(wrapper.vm.shouldConfirmClose).toBe(true);
    });

    it("should not require confirmation when no data to lose", () => {
      wrapper.vm.currentStep = 0;
      wrapper.vm.bibData.parsedEntries = [];
      wrapper.vm.pdfData.totalFiles = 0;
      wrapper.vm.uploadData.confirmedDocuments = {};

      expect(wrapper.vm.shouldConfirmClose).toBe(false);
    });
  });

  describe("Import Completion Events", () => {
    it("should emit import-completed event when closing from summary step", () => {
      wrapper.vm.currentStep = 3;
      wrapper.vm.handleClose();

      expect(wrapper.emitted("import-completed")).toBeTruthy();
      expect(wrapper.emitted("close")).toBeTruthy();
    });

    it("should emit import-completed event when completing import", () => {
      wrapper.vm.handleComplete();

      expect(wrapper.emitted("import-completed")).toBeTruthy();
    });

    it("should emit import-completed event when returning to library", () => {
      wrapper.vm.handleReturnToLibrary();

      expect(wrapper.emitted("import-completed")).toBeTruthy();
      expect(wrapper.emitted("close")).toBeTruthy();
      expect(wrapper.emitted("navigate-to-library")).toBeTruthy();
    });
  });

  describe("Flexible Upload Order", () => {
    it("should allow proceeding with only bibliography uploaded", async () => {
      await wrapper.setProps({ workspace: { id: "test-workspace" } });
      wrapper.vm.bibData.parsedEntries = [{ reference: "test" }];
      wrapper.vm.pdfData.matchedFiles = []; // No PDFs uploaded
      wrapper.vm.hasError = false;

      expect(wrapper.vm.canGoNext).toBe(true);
    });

    it("should validate step with only bibliography uploaded", async () => {
      await wrapper.setProps({ workspace: { id: "test-workspace" } });
      wrapper.vm.bibData.parsedEntries = [{ reference: "test" }];
      wrapper.vm.pdfData.matchedFiles = []; // No PDFs uploaded
      wrapper.vm.hasError = false;

      let isValid = false;
      wrapper.vm.handleValidateStep({
        step: 0,
        callback: (valid) => {
          isValid = valid;
        },
      });

      expect(isValid).toBe(true);
    });
  });
});
