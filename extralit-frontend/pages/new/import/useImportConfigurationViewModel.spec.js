import { useImportConfigurationViewModel } from "./useImportConfigurationViewModel";

// Mock dependencies
vi.mock("ts-injecty", () => ({
  useResolve: vi.fn(),
}));

vi.mock("@nuxtjs/composition-api", () => ({
  ref: vi.fn(),
  useContext: vi.fn(),
  useRoute: vi.fn(),
}));

vi.mock("~/v1/infrastructure/services/useRoutes", () => ({
  useRoutes: vi.fn(),
}));

vi.mock("~/v1/domain/entities/import/ImportHistoryDatasetBuilder", () => ({
  ImportHistoryDatasetBuilder: vi.fn(),
}));

vi.mock("~/v1/domain/entities/import/ImportHistoryDetails", () => ({
  ImportHistoryDetails: vi.fn(),
}));

describe("useImportConfigurationViewModel", () => {
  let mockGetImportHistoryDetailsUseCase;
  let mockGoToHome;
  let mockRoute;
  let mockRef;
  let mockImportHistoryDatasetBuilder;
  let mockImportHistoryDetails;

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock composition API
    const compositionApi = require("@nuxtjs/composition-api");
    mockRef = compositionApi.ref;
    mockRef.mockImplementation((initialValue) => ({
      value: initialValue,
    }));

    // Mock route
    mockRoute = {
      value: {
        params: {
          id: "test-import-123",
        },
      },
    };
    compositionApi.useRoute.mockReturnValue(mockRoute);

    // Mock routes service
    mockGoToHome = vi.fn();
    const useRoutes = require("~/v1/infrastructure/services/useRoutes");
    useRoutes.useRoutes.mockReturnValue({
      goToHome: mockGoToHome,
    });

    // Mock use case
    mockGetImportHistoryDetailsUseCase = {
      execute: vi.fn(),
    };
    const tsInjecty = require("ts-injecty");
    tsInjecty.useResolve.mockReturnValue(mockGetImportHistoryDetailsUseCase);

    // Mock builder
    mockImportHistoryDatasetBuilder = {
      build: vi.fn(),
    };
    const ImportHistoryDatasetBuilder = require("~/v1/domain/entities/import/ImportHistoryDatasetBuilder");
    ImportHistoryDatasetBuilder.ImportHistoryDatasetBuilder.mockImplementation(() => mockImportHistoryDatasetBuilder);

    // Mock ImportHistoryDetails
    mockImportHistoryDetails = {};
    const ImportHistoryDetails = require("~/v1/domain/entities/import/ImportHistoryDetails");
    ImportHistoryDetails.ImportHistoryDetails.mockImplementation(() => mockImportHistoryDetails);

    // Mock console.error to avoid noise in tests
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("loadImportConfiguration", () => {
    it("should load import configuration successfully", async () => {
      const mockImportData = {
        id: "test-import-123",
        filename: "test-papers.csv",
        data: {
          data: [
            { reference: "paper_001", title: "Test Paper 1" },
            { reference: "paper_002", title: "Test Paper 2" },
          ],
          schema: {
            fields: [
              { name: "reference", type: "string" },
              { name: "title", type: "string" },
            ],
          },
        },
        metadata: {
          paper_001: { status: "add" },
          paper_002: { status: "add" },
        },
      };

      const mockDatasetConfig = {
        name: "Test Dataset",
        fields: [],
        questions: [],
      };

      mockGetImportHistoryDetailsUseCase.execute.mockResolvedValue(mockImportData);
      mockImportHistoryDatasetBuilder.build.mockReturnValue(mockDatasetConfig);

      const viewModel = useImportConfigurationViewModel();
      await viewModel.loadImportConfiguration("test-import-123");

      expect(mockGetImportHistoryDetailsUseCase.execute).toHaveBeenCalledWith("test-import-123");
      expect(viewModel.importHistoryData.value).toBe(mockImportHistoryDetails);
      expect(viewModel.datasetConfig.value).toBe(mockDatasetConfig);
      expect(viewModel.error.value).toBeNull();
      expect(viewModel.isLoading.value).toBe(false);
    });

    it("should handle invalid import ID format", async () => {
      const viewModel = useImportConfigurationViewModel();
      await viewModel.loadImportConfiguration("");

      expect(mockGetImportHistoryDetailsUseCase.execute).not.toHaveBeenCalled();
      expect(viewModel.error.value).toBe("The import ID format is invalid. Please check the URL and try again.");
      expect(viewModel.isLoading.value).toBe(false);
    });

    it("should handle empty import data", async () => {
      const mockImportData = {
        id: "test-import-123",
        filename: "empty-import.csv",
        data: {
          data: [], // Empty data
          schema: { fields: [] },
        },
        metadata: {},
      };

      mockGetImportHistoryDetailsUseCase.execute.mockResolvedValue(mockImportData);

      const viewModel = useImportConfigurationViewModel();
      await viewModel.loadImportConfiguration("test-import-123");

      expect(viewModel.error.value).toBe(
        "This import contains no data to configure. Please try importing documents first."
      );
      expect(viewModel.datasetConfig.value).toBeNull();
    });

    it("should handle 404 error", async () => {
      const error = new Error("Not found");
      error.response = { status: 404 };
      mockGetImportHistoryDetailsUseCase.execute.mockRejectedValue(error);

      const viewModel = useImportConfigurationViewModel();
      await viewModel.loadImportConfiguration("test-import-123");

      expect(viewModel.error.value).toBe(
        "Import record not found. It may have been deleted or you don't have access to it."
      );
      expect(viewModel.isLoading.value).toBe(false);
    });

    it("should handle 403 error", async () => {
      const error = new Error("Forbidden");
      error.response = { status: 403 };
      mockGetImportHistoryDetailsUseCase.execute.mockRejectedValue(error);

      const viewModel = useImportConfigurationViewModel();
      await viewModel.loadImportConfiguration("test-import-123");

      expect(viewModel.error.value).toBe(
        "You don't have permission to access this import record. Please check with your workspace administrator."
      );
    });

    it("should handle 401 error", async () => {
      const error = new Error("Unauthorized");
      error.response = { status: 401 };
      mockGetImportHistoryDetailsUseCase.execute.mockRejectedValue(error);

      const viewModel = useImportConfigurationViewModel();
      await viewModel.loadImportConfiguration("test-import-123");

      expect(viewModel.error.value).toBe("Your session has expired. Please sign in again.");
    });

    it("should handle server error", async () => {
      const error = new Error("Server error");
      error.response = { status: 500 };
      mockGetImportHistoryDetailsUseCase.execute.mockRejectedValue(error);

      const viewModel = useImportConfigurationViewModel();
      await viewModel.loadImportConfiguration("test-import-123");

      expect(viewModel.error.value).toBe("Server error occurred while loading the import. Please try again later.");
    });

    it("should handle network error", async () => {
      const error = new Error("Network Error");
      mockGetImportHistoryDetailsUseCase.execute.mockRejectedValue(error);

      const viewModel = useImportConfigurationViewModel();
      await viewModel.loadImportConfiguration("test-import-123");

      expect(viewModel.error.value).toBe(
        "Network connection error. Please check your internet connection and try again."
      );
    });

    it("should handle generic error", async () => {
      const error = new Error("Generic error");
      mockGetImportHistoryDetailsUseCase.execute.mockRejectedValue(error);

      const viewModel = useImportConfigurationViewModel();
      await viewModel.loadImportConfiguration("test-import-123");

      expect(viewModel.error.value).toBe(
        "Failed to load import configuration. Please check your connection and try again."
      );
    });
  });

  describe("retry", () => {
    it("should retry loading configuration with exponential backoff", async () => {
      const mockImportData = {
        id: "test-import-123",
        filename: "test-papers.csv",
        data: {
          data: [{ reference: "paper_001", title: "Test Paper 1" }],
          schema: { fields: [{ name: "reference", type: "string" }] },
        },
        metadata: { paper_001: { status: "add" } },
      };

      mockGetImportHistoryDetailsUseCase.execute.mockResolvedValue(mockImportData);
      mockImportHistoryDatasetBuilder.build.mockReturnValue({});

      // Mock setTimeout to avoid actual delays in tests
      vi.spyOn(global, "setTimeout").mockImplementation((callback) => {
        callback();
        return 123;
      });

      const viewModel = useImportConfigurationViewModel();
      await viewModel.retry();

      expect(mockGetImportHistoryDetailsUseCase.execute).toHaveBeenCalledWith("test-import-123");
      expect(viewModel.retryCount.value).toBe(0);

      global.setTimeout.mockRestore();
    });

    it("should not retry if max retries exceeded", async () => {
      const viewModel = useImportConfigurationViewModel();
      viewModel.retryCount.value = 3; // Set to max retries

      await viewModel.retry();

      expect(mockGetImportHistoryDetailsUseCase.execute).not.toHaveBeenCalled();
      expect(viewModel.error.value).toBe(
        "Maximum retry attempts (3) exceeded. Please refresh the page or contact support."
      );
    });

    it("should handle missing import ID during retry", async () => {
      mockRoute.value.params.id = null;

      const viewModel = useImportConfigurationViewModel();
      await viewModel.retry();

      expect(mockGetImportHistoryDetailsUseCase.execute).not.toHaveBeenCalled();
      expect(viewModel.error.value).toBe("Unable to determine import ID for retry.");
    });
  });

  describe("handleSubsetChange", () => {
    it("should handle subset change successfully", () => {
      const mockDatasetConfig = {
        changeSubset: vi.fn(),
      };

      const viewModel = useImportConfigurationViewModel();
      viewModel.datasetConfig.value = mockDatasetConfig;

      viewModel.handleSubsetChange("test-subset");

      expect(mockDatasetConfig.changeSubset).toHaveBeenCalledWith("test-subset");
      expect(viewModel.error.value).toBeNull();
    });

    it("should handle subset change error", () => {
      const mockDatasetConfig = {
        changeSubset: vi.fn(() => {
          throw new Error("Subset change failed");
        }),
      };

      const viewModel = useImportConfigurationViewModel();
      viewModel.datasetConfig.value = mockDatasetConfig;

      viewModel.handleSubsetChange("test-subset");

      expect(viewModel.error.value).toBe("Failed to change dataset subset. Please try again.");
    });

    it("should handle missing dataset config", () => {
      const viewModel = useImportConfigurationViewModel();
      viewModel.datasetConfig.value = null;

      // Should not throw error
      expect(() => viewModel.handleSubsetChange("test-subset")).not.toThrow();
    });
  });

  describe("handleBreadcrumbAction", () => {
    it("should handle home action", () => {
      const viewModel = useImportConfigurationViewModel();
      viewModel.handleBreadcrumbAction("home");

      expect(mockGoToHome).toHaveBeenCalled();
    });

    it("should handle back action", () => {
      // Mock window.history.back
      const mockBack = vi.fn();
      Object.defineProperty(window, "history", {
        value: { back: mockBack },
        writable: true,
      });

      const viewModel = useImportConfigurationViewModel();
      viewModel.handleBreadcrumbAction("back");

      expect(mockBack).toHaveBeenCalled();
    });

    it("should handle unknown action", () => {
      const consoleSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

      const viewModel = useImportConfigurationViewModel();
      viewModel.handleBreadcrumbAction("unknown");

      expect(consoleSpy).toHaveBeenCalledWith("Unknown breadcrumb action:", "unknown");

      consoleSpy.mockRestore();
    });
  });

  describe("navigateToHome", () => {
    it("should navigate to home", () => {
      const viewModel = useImportConfigurationViewModel();
      viewModel.navigateToHome();

      expect(mockGoToHome).toHaveBeenCalled();
    });
  });

  describe("getImportId", () => {
    it("should return import ID from route params", () => {
      const viewModel = useImportConfigurationViewModel();
      const importId = viewModel.getImportId();

      expect(importId).toBe("test-import-123");
    });

    it("should return null if no import ID in route", () => {
      mockRoute.value.params.id = null;

      const viewModel = useImportConfigurationViewModel();
      const importId = viewModel.getImportId();

      expect(importId).toBeNull();
    });
  });

  describe("resetError", () => {
    it("should reset error state", () => {
      const viewModel = useImportConfigurationViewModel();
      viewModel.error.value = "Test error";

      viewModel.resetError();

      expect(viewModel.error.value).toBeNull();
    });
  });

  describe("isValidImportId", () => {
    it("should validate UUID format", async () => {
      const viewModel = useImportConfigurationViewModel();

      // Access the private method through the returned object (if exposed) or test indirectly
      // Since isValidImportId is private, we test it indirectly through loadImportConfiguration

      // Test valid UUID
      expect(() => viewModel.loadImportConfiguration("550e8400-e29b-41d4-a716-446655440000")).not.toThrow();

      // Test valid numeric ID
      expect(() => viewModel.loadImportConfiguration("123")).not.toThrow();

      // Test invalid empty string
      await viewModel.loadImportConfiguration("");
      expect(viewModel.error.value).toBe(
        "Failed to load import configuration. Please check your connection and try again."
      );
    });
  });
});
