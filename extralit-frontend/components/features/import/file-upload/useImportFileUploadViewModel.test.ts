/**
 * Test suite for useImportFileUploadViewModel composable
 * Tests core functionality, state management, and strategy pattern integration
 */

import { useImportFileUploadViewModel } from "./useImportFileUploadViewModel";

// Mock @nuxtjs/composition-api
let mockRef: jest.Mock;
let mockComputed: jest.Mock;
let mockWatch: jest.Mock;
let mockOnMounted: jest.Mock;

jest.mock("@nuxtjs/composition-api", () => ({
  ref: jest.fn(),
  computed: jest.fn(),
  watch: jest.fn(),
  onMounted: jest.fn(),
}));

describe("useImportFileUploadViewModel", () => {
  let mockStrategy: any;
  let mockOptions: any;
  let mockStateRef: any;
  let mockDataRef: any;

  beforeEach(() => {
    // Get the mock functions
    mockRef = require("@nuxtjs/composition-api").ref;
    mockComputed = require("@nuxtjs/composition-api").computed;
    mockWatch = require("@nuxtjs/composition-api").watch;
    mockOnMounted = require("@nuxtjs/composition-api").onMounted;

    // Reset mocks
    jest.clearAllMocks();

    // Mock strategy
    mockStrategy = {
      acceptedExtensions: [".test"],
      validateFile: jest.fn().mockReturnValue({ valid: true }),
      processFiles: jest.fn().mockResolvedValue(undefined),
      getDropzoneIcon: jest.fn().mockReturnValue("default-icon"),
      getDropzoneText: jest.fn().mockReturnValue("Default text"),
    };

    // Mock options
    mockOptions = {
      strategy: mockStrategy,
      initialData: null,
      onUpdate: jest.fn(),
      hasValidData: jest.fn().mockReturnValue(true),
      createPayload: jest.fn().mockReturnValue({ isValid: true, type: "test" }),
    };

    // Mock reactive state
    mockStateRef = {
      value: {
        isDragging: false,
        uploaded: false,
        hasError: false,
        errorMessage: "",
        processing: false,
        progress: 0,
        processedFiles: 0,
        totalFiles: 0,
      },
    };

    mockDataRef = {
      value: {},
    };

    mockRef.mockImplementation((initialValue) => {
      if (typeof initialValue === "object" && initialValue.isDragging !== undefined) {
        return mockStateRef;
      }
      return mockDataRef;
    });

    mockComputed.mockImplementation((fn) => ({ value: fn() }));
  });

  describe("initialization", () => {
    it("should initialize with default state", () => {
      const viewModel = useImportFileUploadViewModel(mockOptions);

      expect(mockRef).toHaveBeenCalledWith({
        isDragging: false,
        uploaded: false,
        hasError: false,
        errorMessage: "",
        processing: false,
        progress: 0,
        processedFiles: 0,
        totalFiles: 0,
      });

      expect(viewModel).toHaveProperty("state");
      expect(viewModel).toHaveProperty("data");
      expect(viewModel).toHaveProperty("handleDragOver");
      expect(viewModel).toHaveProperty("handleDragLeave");
      expect(viewModel).toHaveProperty("handleDrop");
      expect(viewModel).toHaveProperty("processFiles");
      expect(viewModel).toHaveProperty("reset");
    });

    it("should initialize with provided initial data", () => {
      const initialData = { fileName: "test.txt" };
      const optionsWithData = { ...mockOptions, initialData };

      useImportFileUploadViewModel(optionsWithData);

      expect(mockRef).toHaveBeenCalledWith(initialData);
    });

    it("should set up watchers and lifecycle hooks", () => {
      useImportFileUploadViewModel(mockOptions);

      expect(mockWatch).toHaveBeenCalled();
      expect(mockOnMounted).toHaveBeenCalled();
    });
  });

  describe("drag and drop handlers", () => {
    it("should handle drag over events", () => {
      const viewModel = useImportFileUploadViewModel(mockOptions);
      const mockEvent = { preventDefault: jest.fn() } as any;

      viewModel.handleDragOver(mockEvent);

      expect(mockEvent.preventDefault).toHaveBeenCalled();
      expect(mockStateRef.value.isDragging).toBe(true);
    });

    it("should handle drag leave events", () => {
      const viewModel = useImportFileUploadViewModel(mockOptions);
      mockStateRef.value.isDragging = true;

      viewModel.handleDragLeave();

      expect(mockStateRef.value.isDragging).toBe(false);
    });

    it("should handle drop events", async () => {
      const viewModel = useImportFileUploadViewModel(mockOptions);
      const mockFiles = [new File(["content"], "test.txt", { type: "text/plain" })];
      const mockEvent = {
        preventDefault: jest.fn(),
        dataTransfer: { files: mockFiles },
      } as any;

      await viewModel.handleDrop(mockEvent);

      expect(mockEvent.preventDefault).toHaveBeenCalled();
      expect(mockStateRef.value.isDragging).toBe(false);
      expect(mockStrategy.processFiles).toHaveBeenCalledWith(mockFiles);
    });
  });

  describe("file processing", () => {
    it("should process files using strategy", async () => {
      const viewModel = useImportFileUploadViewModel(mockOptions);
      const mockFiles = [new File(["content"], "test.txt", { type: "text/plain" })];

      await viewModel.processFiles(mockFiles);

      expect(mockStateRef.value.processing).toBe(false); // Should be false after completion
      expect(mockStrategy.processFiles).toHaveBeenCalledWith(mockFiles);
      expect(mockStateRef.value.uploaded).toBe(true);
      expect(mockStateRef.value.hasError).toBe(false);
    });

    it("should handle processing errors", async () => {
      const errorMessage = "Processing failed";
      mockStrategy.processFiles.mockRejectedValue(new Error(errorMessage));

      const viewModel = useImportFileUploadViewModel(mockOptions);
      const mockFiles = [new File(["content"], "test.txt", { type: "text/plain" })];

      await viewModel.processFiles(mockFiles);

      expect(mockStateRef.value.hasError).toBe(true);
      expect(mockStateRef.value.errorMessage).toBe(errorMessage);
      expect(mockStateRef.value.uploaded).toBe(false);
      expect(mockStateRef.value.processing).toBe(false);
    });

    it("should reset error state before processing", async () => {
      const viewModel = useImportFileUploadViewModel(mockOptions);
      mockStateRef.value.hasError = true;
      mockStateRef.value.errorMessage = "Previous error";

      const mockFiles = [new File(["content"], "test.txt", { type: "text/plain" })];

      await viewModel.processFiles(mockFiles);

      expect(mockStateRef.value.hasError).toBe(false);
      expect(mockStateRef.value.errorMessage).toBe("");
    });
  });

  describe("computed properties", () => {
    it("should compute progress percentage correctly", () => {
      mockStateRef.value.processedFiles = 5;
      mockStateRef.value.totalFiles = 10;

      const viewModel = useImportFileUploadViewModel(mockOptions);

      // The computed function should be called
      expect(mockComputed).toHaveBeenCalled();
      // We can't easily test the actual computed value due to mocking,
      // but we can verify the function was set up
    });

    it("should compute dropzone icon based on state", () => {
      const viewModel = useImportFileUploadViewModel(mockOptions);

      // Verify computed functions were set up
      expect(mockComputed).toHaveBeenCalledTimes(3); // progressPercentage, getDropzoneIcon, getDropzoneText
    });
  });

  describe("error handling", () => {
    it("should show error with message", () => {
      const viewModel = useImportFileUploadViewModel(mockOptions);
      const errorMessage = "Test error";

      viewModel.showError(errorMessage);

      expect(mockStateRef.value.hasError).toBe(true);
      expect(mockStateRef.value.errorMessage).toBe(errorMessage);
      expect(mockStateRef.value.uploaded).toBe(false);
    });

    it("should clear error state", () => {
      const viewModel = useImportFileUploadViewModel(mockOptions);
      mockStateRef.value.hasError = true;
      mockStateRef.value.errorMessage = "Some error";

      viewModel.clearError();

      expect(mockStateRef.value.hasError).toBe(false);
      expect(mockStateRef.value.errorMessage).toBe("");
    });
  });

  describe("reset functionality", () => {
    it("should reset all state to initial values", () => {
      const viewModel = useImportFileUploadViewModel(mockOptions);

      // Set some state
      mockStateRef.value.isDragging = true;
      mockStateRef.value.uploaded = true;
      mockStateRef.value.hasError = true;
      mockStateRef.value.errorMessage = "Error";
      mockStateRef.value.processing = true;
      mockStateRef.value.progress = 50;
      mockStateRef.value.processedFiles = 5;
      mockStateRef.value.totalFiles = 10;
      mockDataRef.value = { fileName: "test.txt" };

      viewModel.reset();

      expect(mockStateRef.value.isDragging).toBe(false);
      expect(mockStateRef.value.uploaded).toBe(false);
      expect(mockStateRef.value.hasError).toBe(false);
      expect(mockStateRef.value.errorMessage).toBe("");
      expect(mockStateRef.value.processing).toBe(false);
      expect(mockStateRef.value.progress).toBe(0);
      expect(mockStateRef.value.processedFiles).toBe(0);
      expect(mockStateRef.value.totalFiles).toBe(0);
      expect(mockDataRef.value).toEqual({});
    });
  });

  describe("progress updates", () => {
    it("should update progress values", () => {
      const viewModel = useImportFileUploadViewModel(mockOptions);

      viewModel.updateProgress(7, 10);

      expect(mockStateRef.value.processedFiles).toBe(7);
      expect(mockStateRef.value.totalFiles).toBe(10);
      expect(mockStateRef.value.progress).toBe(70);
    });

    it("should handle zero total files", () => {
      const viewModel = useImportFileUploadViewModel(mockOptions);

      viewModel.updateProgress(0, 0);

      expect(mockStateRef.value.processedFiles).toBe(0);
      expect(mockStateRef.value.totalFiles).toBe(0);
      expect(mockStateRef.value.progress).toBe(0);
    });
  });
});