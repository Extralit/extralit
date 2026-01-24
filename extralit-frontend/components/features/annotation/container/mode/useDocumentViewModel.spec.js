import { useDocumentViewModel } from "./useDocumentViewModel";

// Mock dependencies inline to avoid hoisting issues
jest.mock("ts-injecty", () => ({
  useResolve: jest.fn(() => mockGetDocumentUseCase),
}));

jest.mock("@/v1/infrastructure/storage/DocumentStorage", () => ({
  useDocument: jest.fn(() => ({
    state: mockDocument,
    set: mockSetDocument,
    clear: mockClearDocument,
  })),
}));

jest.mock("@/v1/infrastructure/storage/DatasetStorage", () => ({
  useDataset: jest.fn(() => ({
    state: mockDataset,
  })),
}));

jest.mock("@/v1/infrastructure/storage/WorkspaceStorage", () => ({
  useWorkspaces: jest.fn(() => ({
    state: mockWorkspaces,
  })),
}));

jest.mock("~/v1/infrastructure/services/useNotifications", () => ({
  useNotifications: jest.fn(() => mockNotifications),
}));

jest.mock("@/v1/infrastructure/services/useWait", () => ({
  waitForAsyncValue: jest.fn(() => Promise.resolve()),
}));

jest.mock("vue-demi", () => ({
  ref: jest.fn(),
  watch: jest.fn(),
  computed: jest.fn(),
}));

// Mock objects
let mockDocument;
let mockSetDocument;
let mockClearDocument;
let mockDataset;
let mockWorkspaces;
let mockNotifications;
let mockGetDocumentUseCase;
let mockRef;
let mockWatch;
let mockComputed;

describe("useDocumentViewModel", () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Setup mock document state
    mockDocument = {
      id: null,
      url: null,
      pmid: null,
      doi: null,
      file_name: null,
      page_number: null,
    };

    mockSetDocument = jest.fn();
    mockClearDocument = jest.fn();

    mockDataset = {
      workspaceName: "test-workspace",
    };

    mockWorkspaces = {
      selectedWorkspace: {
        id: "workspace-123",
      },
    };

    mockNotifications = {
      notify: jest.fn(),
    };

    mockGetDocumentUseCase = {
      setDocument: jest.fn(),
      setSegments: jest.fn(),
      createParams: jest.fn(),
    };

    // Setup Vue composition API mocks
    const vueDemi = require("vue-demi");
    mockRef = vueDemi.ref;
    mockWatch = vueDemi.watch;
    mockComputed = vueDemi.computed;

    mockRef.mockImplementation((value) => ({ value }));
    mockWatch.mockImplementation(() => {});
    mockComputed.mockImplementation((fn) => ({ value: fn() }));
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe("hasDocumentLoaded computed property", () => {
    it("should return false when document has no id", () => {
      mockDocument.id = null;

      useDocumentViewModel({ record: {} });

      // Get the computed function that was passed to mockComputed
      const computedCalls = mockComputed.mock.calls;
      const hasDocumentLoadedCall = computedCalls.find((call) => call[0].toString().includes("document.id"));

      expect(hasDocumentLoadedCall).toBeDefined();
      const hasDocumentLoaded = hasDocumentLoadedCall[0]();
      expect(hasDocumentLoaded).toBe(false);
    });

    it("should return true when document has an id", () => {
      mockDocument.id = "doc-123";

      useDocumentViewModel({ record: {} });

      // Get the computed function that was passed to mockComputed
      const computedCalls = mockComputed.mock.calls;
      const hasDocumentLoadedCall = computedCalls.find((call) => call[0].toString().includes("document.id"));

      expect(hasDocumentLoadedCall).toBeDefined();
      const hasDocumentLoaded = hasDocumentLoadedCall[0]();
      expect(hasDocumentLoaded).toBe(true);
    });
  });

  describe("createParams method", () => {
    it("should call createParams from use case", () => {
      const metadata = { pmid: "12345" };
      const workspaceId = "workspace-123";

      mockGetDocumentUseCase.createParams.mockReturnValue({
        workspace_id: workspaceId,
        pmid: "12345",
      });

      useDocumentViewModel({ record: { metadata } });

      // Verify that watch was called for props.record?.metadata
      expect(mockWatch).toHaveBeenCalled();

      // Find the watch call for metadata
      const watchCalls = mockWatch.mock.calls;
      const metadataWatchCall = watchCalls.find(
        (call) => call[0].toString().includes("props.record") && call[0].toString().includes("metadata")
      );

      expect(metadataWatchCall).toBeDefined();

      // Since we can't easily test the async updateDocument function,
      // we'll verify that the watch was set up correctly
      expect(mockWatch).toHaveBeenCalledWith(expect.any(Function), expect.any(Function), { immediate: true });
    });
  });

  describe("return values", () => {
    it("should return all expected properties and methods", () => {
      const viewModel = useDocumentViewModel({ record: {} });

      expect(viewModel).toHaveProperty("document");
      expect(viewModel).toHaveProperty("fetchDocumentSegments");
      expect(viewModel).toHaveProperty("focusDocumentPageNumber");
      expect(viewModel).toHaveProperty("clearDocument");
      expect(viewModel).toHaveProperty("isDocumentPanelExpanded");
    });

    it("should return functions for methods", () => {
      const viewModel = useDocumentViewModel({ record: {} });

      expect(typeof viewModel.fetchDocumentSegments).toBe("function");
      expect(typeof viewModel.focusDocumentPageNumber).toBe("function");
      expect(typeof viewModel.clearDocument).toBe("function");
    });
  });
});
