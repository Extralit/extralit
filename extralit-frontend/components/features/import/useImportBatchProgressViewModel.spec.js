import { useImportBatchProgressViewModel } from "./useImportBatchProgressViewModel";

// Mock dependencies
jest.mock("~/v1/domain/usecases/bulk-upload-documents-use-case", () => ({
  BulkUploadDocumentsUseCase: jest.fn(),
}));

jest.mock("~/v1/domain/usecases/get-job-status-use-case", () => ({
  GetJobStatusUseCase: jest.fn(),
}));

jest.mock("~/v1/domain/usecases/create-import-history-use-case", () => ({
  CreateImportHistoryUseCase: jest.fn(),
}));

jest.mock("ts-injecty", () => ({
  useResolve: jest.fn(() => ({})),
}));

describe("useImportBatchProgressViewModel", () => {
  let viewModel;

  beforeEach(() => {
    // Mock the use cases
    const mockProps = {
      workspace: { id: "workspace-1" },
      uploadData: { confirmedDocuments: {} },
      bibFileName: "test.bib",
    };

    viewModel = useImportBatchProgressViewModel(mockProps);
  });

  describe("createNormalizedSummary", () => {
    const mockConfirmedDocuments = {
      ref1: {
        document_create: { reference: "ref1", title: "Paper 1" },
        associated_files: [{ filename: "paper1.pdf", size: 1000 }],
      },
      ref2: {
        document_create: { reference: "ref2", title: "Paper 2" },
        associated_files: [{ filename: "paper2.pdf", size: 2000 }],
      },
      ref3: {
        document_create: { reference: "ref3", title: "Paper 3" },
        associated_files: [{ filename: "paper3.pdf", size: 3000 }],
      },
    };

    const mockDocumentActions = {
      ref1: "add",
      ref2: "update",
      ref3: "add",
    };

    const mockAllJobIds = {
      ref1: "job-1",
      ref2: "job-2",
      ref3: "job-3",
    };

    it("correctly counts added and updated documents when all jobs succeed", () => {
      const mockJobStatuses = {
        "job-1": "finished", // ref1 - add
        "job-2": "finished", // ref2 - update
        "job-3": "finished", // ref3 - add
      };

      const mockErrors = [];

      const result = viewModel.createNormalizedSummary(
        mockConfirmedDocuments,
        mockDocumentActions,
        mockAllJobIds,
        mockJobStatuses,
        mockErrors
      );

      expect(result.total).toBe(3);
      expect(result.added).toBe(2); // ref1 and ref3
      expect(result.updated).toBe(1); // ref2
      expect(result.skipped).toBe(0);
      expect(result.failed).toBe(0);
      expect(result.errors).toEqual([]);
    });

    it("correctly counts failed documents", () => {
      const mockJobStatuses = {
        "job-1": "finished", // ref1 - add (success)
        "job-2": "failed", // ref2 - update (failed)
        "job-3": "failed", // ref3 - add (failed)
      };

      const mockErrors = [
        { reference: "ref2", message: "Upload failed" },
        { reference: "ref3", message: "File corrupted" },
      ];

      const result = viewModel.createNormalizedSummary(
        mockConfirmedDocuments,
        mockDocumentActions,
        mockAllJobIds,
        mockJobStatuses,
        mockErrors
      );

      expect(result.total).toBe(3);
      expect(result.added).toBe(1); // ref1 only
      expect(result.updated).toBe(0); // ref2 failed
      expect(result.skipped).toBe(0);
      expect(result.failed).toBe(2); // ref2 and ref3
      expect(result.errors).toEqual([
        { reference: "ref2", message: "Upload failed" },
        { reference: "ref3", message: "File corrupted" },
      ]);
    });

    it("handles mixed job statuses correctly", () => {
      const mockJobStatuses = {
        "job-1": "finished", // ref1 - add (success)
        "job-2": "failed", // ref2 - update (failed)
        "job-3": "started", // ref3 - add (in progress)
      };

      const mockErrors = [{ reference: "ref2", message: "Network error" }];

      const result = viewModel.createNormalizedSummary(
        mockConfirmedDocuments,
        mockDocumentActions,
        mockAllJobIds,
        mockJobStatuses,
        mockErrors
      );

      expect(result.total).toBe(3);
      expect(result.added).toBe(1); // ref1 only (ref3 still in progress)
      expect(result.updated).toBe(0); // ref2 failed
      expect(result.skipped).toBe(0);
      expect(result.failed).toBe(1); // ref2 only
      expect(result.errors).toEqual([{ reference: "ref2", message: "Network error" }]);
    });

    it("handles missing job IDs gracefully", () => {
      const mockJobStatusesPartial = {
        "job-1": "finished", // ref1 - add (success)
        "job-2": "failed", // ref2 - update (failed)
        // job-3 missing
      };

      const mockAllJobIdsPartial = {
        ref1: "job-1",
        ref2: "job-2",
        // ref3 missing
      };

      const mockErrors = [{ reference: "ref2", message: "Upload failed" }];

      const result = viewModel.createNormalizedSummary(
        mockConfirmedDocuments,
        mockDocumentActions,
        mockAllJobIdsPartial,
        mockJobStatusesPartial,
        mockErrors
      );

      expect(result.total).toBe(3);
      expect(result.added).toBe(1); // ref1 only
      expect(result.updated).toBe(0); // ref2 failed
      expect(result.skipped).toBe(0);
      expect(result.failed).toBe(1); // ref2 only
      // ref3 is not counted in any completion bucket since no job ID/status
    });

    it("defaults to 'add' status when document action is missing", () => {
      const mockDocumentActionsPartial = {
        ref1: "add",
        // ref2 and ref3 missing - should default to 'add'
      };

      const mockJobStatuses = {
        "job-1": "finished",
        "job-2": "finished",
        "job-3": "finished",
      };

      const result = viewModel.createNormalizedSummary(
        mockConfirmedDocuments,
        mockDocumentActionsPartial,
        mockAllJobIds,
        mockJobStatuses,
        []
      );

      expect(result.total).toBe(3);
      expect(result.added).toBe(3); // all default to 'add'
      expect(result.updated).toBe(0);
      expect(result.skipped).toBe(0);
      expect(result.failed).toBe(0);
    });

    it("handles empty inputs gracefully", () => {
      const result = viewModel.createNormalizedSummary({}, {}, {}, {}, []);

      expect(result.total).toBe(0);
      expect(result.added).toBe(0);
      expect(result.updated).toBe(0);
      expect(result.skipped).toBe(0);
      expect(result.failed).toBe(0);
      expect(result.errors).toEqual([]);
      expect(typeof result.importId).toBe("string");
    });
  });
});
