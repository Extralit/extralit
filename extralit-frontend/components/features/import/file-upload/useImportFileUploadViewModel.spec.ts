import { useImportFileUploadViewModel } from "./useImportFileUploadViewModel";

// Mock the dependencies
jest.mock("ts-injecty", () => ({
  useResolve: jest.fn(),
}));

jest.mock("~/v1/domain/entities/table/TableData", () => ({
  TableData: jest.fn().mockImplementation((data, schema, validation) => ({
    data,
    schema,
    validation,
  })),
}));

jest.mock("~/v1/domain/entities/table/Schema", () => ({
  DataFrameSchema: jest.fn().mockImplementation((fields, primaryKey, foreignKeys, name) => ({
    fields,
    primaryKey,
    foreignKeys,
    name,
  })),
  DataFrameField: jest.fn(),
}));

jest.mock("~/v1/domain/entities/table/Validation", () => ({
  Validators: jest.fn(),
}));

describe("useImportFileUploadViewModel", () => {
  let emit: jest.Mock;
  let props: any;

  beforeEach(() => {
    emit = jest.fn();
    props = {
      initialBibData: {
        fileName: "",
        dataframeData: null,
        rawContent: "",
      },
      initialPdfData: {
        matchedFiles: [],
        unmatchedFiles: [],
        totalFiles: 0,
      },
    };
  });

  describe("shouldShowEditableTable", () => {
    it("should return true when PDFs are uploaded but no bibliography", () => {
      const viewModel = useImportFileUploadViewModel(props, { emit });

      // Simulate PDF upload
      viewModel.handlePdfUpdate({
        matchedFiles: [],
        unmatchedFiles: [{ name: "test.pdf" }],
        totalFiles: 1,
      });

      expect(viewModel.shouldShowEditableTable.value).toBe(true);
    });

    it("should return false when no PDFs are uploaded", () => {
      const viewModel = useImportFileUploadViewModel(props, { emit });

      expect(viewModel.shouldShowEditableTable.value).toBe(false);
    });

    it("should return false when bibliography is uploaded", () => {
      const viewModel = useImportFileUploadViewModel(props, { emit });

      // Simulate PDF upload
      viewModel.handlePdfUpdate({
        matchedFiles: [],
        unmatchedFiles: [{ name: "test.pdf" }],
        totalFiles: 1,
      });

      // Simulate bibliography upload
      viewModel.handleBibUpdate({
        fileName: "test.bib",
        dataframeData: {
          data: [{ reference: "test2023", title: "Test Paper" }],
          schema: {},
        },
        rawContent: "",
      });

      expect(viewModel.shouldShowEditableTable.value).toBe(false);
    });
  });

  describe("editableTableColumns", () => {
    it("should include reference and files columns with proper configuration", () => {
      const viewModel = useImportFileUploadViewModel(props, { emit });

      // Simulate PDF upload
      viewModel.handlePdfUpdate({
        matchedFiles: [],
        unmatchedFiles: [{ name: "test1.pdf" }, { name: "test2.pdf" }],
        totalFiles: 2,
      });

      const columns = viewModel.editableTableColumns.value;
      const referenceCol = columns.find((col: any) => col.field === "reference") as any;
      const filesCol = columns.find((col: any) => col.field === "files") as any;

      expect(referenceCol).toBeDefined();
      expect(referenceCol?.frozen).toBe(true);
      expect(referenceCol?.validator).toContain("required");
      expect(referenceCol?.validator).toContain("unique");

      expect(filesCol).toBeDefined();
      expect(filesCol?.editor).toBe("list");

      // editorParams is a function for dynamic Tabulator params; call it with a mock cell
      const mockCell = {
        getTable: () => ({ getRows: () => [] }),
        getRow: () => ({ getData: () => ({}) }),
        getField: () => "files",
        getValue: () => [],
      };
      const editorParams = typeof filesCol?.editorParams === "function"
        ? filesCol.editorParams(mockCell)
        : filesCol?.editorParams;

      expect(editorParams?.multiselect).toBe(true);
      expect(editorParams?.values).toHaveLength(2);
    });
  });

  describe("unmappedPdfFiles", () => {
    it("should return all PDFs when no files are assigned", () => {
      const viewModel = useImportFileUploadViewModel(props, { emit });

      viewModel.handlePdfUpdate({
        matchedFiles: [],
        unmatchedFiles: [{ name: "test1.pdf" }, { name: "test2.pdf" }],
        totalFiles: 2,
      });

      expect(viewModel.unmappedPdfFiles.value).toEqual(["test1.pdf", "test2.pdf"]);
    });

    it("should exclude assigned PDFs from unmapped list", () => {
      const viewModel = useImportFileUploadViewModel(props, { emit });

      viewModel.handlePdfUpdate({
        matchedFiles: [],
        unmatchedFiles: [{ name: "test1.pdf" }, { name: "test2.pdf" }],
        totalFiles: 2,
      });

      // Manually set table data with one assigned file
      viewModel.editableTableData.value = [
        {
          reference: "test2023",
          files: ["test1.pdf"],
        },
      ];

      expect(viewModel.unmappedPdfFiles.value).toEqual(["test2.pdf"]);
    });
  });

  describe("syncEditableTableToBibData", () => {
    it("should convert editable table data to bibData format", () => {
      const viewModel = useImportFileUploadViewModel(props, { emit });

      viewModel.editableTableData.value = [
        {
          reference: "test2023",
          title: "Test Paper",
          authors: "John Doe",
          year: "2023",
          files: ["test.pdf"],
        },
      ];

      viewModel.syncEditableTableToBibData();

      expect(viewModel.bibData.value.dataframeData).toBeDefined();
      expect(viewModel.bibData.value.dataframeData?.data).toHaveLength(1);
      expect(viewModel.bibData.value.dataframeData?.data[0]).toHaveProperty("reference", "test2023");
      expect(viewModel.bibData.value.dataframeData?.data[0]).toHaveProperty("filePaths");
      expect(viewModel.bibData.value.dataframeData?.data[0].filePaths).toEqual(["test.pdf"]);
    });

    it("should filter out empty rows", () => {
      const viewModel = useImportFileUploadViewModel(props, { emit });

      viewModel.editableTableData.value = [
        {
          reference: "test2023",
          title: "Test Paper",
          files: ["test.pdf"],
        },
        {
          reference: "",
          title: "",
          files: [],
        },
      ];

      viewModel.syncEditableTableToBibData();

      expect(viewModel.bibData.value.dataframeData).toBeDefined();
      expect(viewModel.bibData.value.dataframeData?.data).toHaveLength(1);
    });
  });
});
