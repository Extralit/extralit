import { mount } from "@vue/test-utils";
import ImportHistoryDataPreview from "./ImportHistoryDataPreview.vue";
import { ImportHistoryDetails } from "~/v1/domain/entities/import/ImportHistoryDetails";

// Mock dependencies
jest.mock("~/v1/domain/entities/import/ImportHistoryDetails", () => ({
  ImportHistoryDetails: jest.fn(),
}));

describe("ImportHistoryDataPreview", () => {
  let wrapper;
  let mockImportHistoryDetails;

  beforeEach(() => {
    // Mock ImportHistoryDetails
    mockImportHistoryDetails = {
      filename: "test-papers.csv",
      createdAt: new Date("2024-01-15T10:30:00Z"),
      records: [
        {
          reference: "paper_001",
          title: "Sample Paper Title 1",
          authors: "Author 1, Co-Author 1",
          doi: "10.1000/test1",
          year: 2023,
        },
        {
          reference: "paper_002",
          title: "Sample Paper Title 2",
          authors: "Author 2",
          doi: "10.1000/test2",
          year: 2024,
        },
      ],
      schema: {
        fields: [
          { name: "reference", type: "string", required: true },
          { name: "title", type: "string", required: true },
          { name: "authors", type: "string", required: false },
          { name: "doi", type: "string", required: false },
          { name: "year", type: "integer", required: false },
        ],
      },
      metadata: {
        paper_001: { status: "add" },
        paper_002: { status: "add" },
      },
      summary: {
        total_documents: 2,
        add_count: 2,
        update_count: 0,
        skip_count: 0,
        failed_count: 0,
      },
      getFieldStats: jest.fn(),
    };

    const ImportHistoryDetails = require("~/v1/domain/entities/import/ImportHistoryDetails");
    ImportHistoryDetails.ImportHistoryDetails.mockImplementation(() => mockImportHistoryDetails);
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.destroy();
    }
    jest.restoreAllMocks();
  });

  describe("Loading State", () => {
    it("should display loading state when loading is true", () => {
      wrapper = mount(ImportHistoryDataPreview, {
        propsData: {
          loading: true,
          importHistoryDetails: null,
        },
        stubs: {
          BaseSpinner: {
            template: '<div class="mock-spinner">Loading...</div>',
          },
        },
      });

      expect(wrapper.find(".loading-state").exists()).toBe(true);
      expect(wrapper.find(".mock-spinner").exists()).toBe(true);
      expect(wrapper.text()).toContain("Loading import data...");
    });
  });

  describe("Error State", () => {
    it("should display error state when error prop is provided", () => {
      wrapper = mount(ImportHistoryDataPreview, {
        propsData: {
          loading: false,
          error: "Failed to load import data",
          importHistoryDetails: null,
        },
        stubs: {
          BaseIcon: {
            template: '<div class="mock-icon"></div>',
            props: ["icon-name"],
          },
          BaseButton: {
            template: '<button class="mock-button" @click="$emit(\'click\')"><slot /></button>',
            props: ["variant"],
          },
        },
      });

      expect(wrapper.find(".error-state").exists()).toBe(true);
      expect(wrapper.text()).toContain("Failed to Load Data");
      expect(wrapper.text()).toContain("Failed to load import data");
      expect(wrapper.find(".mock-button").exists()).toBe(true);
    });

    it("should emit retry event when retry button is clicked", async () => {
      wrapper = mount(ImportHistoryDataPreview, {
        propsData: {
          loading: false,
          error: "Network error",
          importHistoryDetails: null,
        },
        stubs: {
          BaseIcon: true,
          BaseButton: {
            template: "<button @click=\"$emit('click')\"><slot /></button>",
            props: ["variant"],
          },
        },
      });

      await wrapper.find("button").trigger("click");

      expect(wrapper.emitted("retry")).toBeTruthy();
      expect(wrapper.emitted("retry")).toHaveLength(1);
    });
  });

  describe("Empty State", () => {
    it("should display empty state when no import history details", () => {
      wrapper = mount(ImportHistoryDataPreview, {
        propsData: {
          loading: false,
          error: null,
          importHistoryDetails: null,
        },
        stubs: {
          BaseIcon: true,
        },
      });

      expect(wrapper.find(".empty-state").exists()).toBe(true);
      expect(wrapper.text()).toContain("No Import Data");
      expect(wrapper.text()).toContain("No import history data available to preview.");
    });
  });

  describe("Main Content", () => {
    beforeEach(() => {
      wrapper = mount(ImportHistoryDataPreview, {
        propsData: {
          loading: false,
          error: null,
          importHistoryDetails: mockImportHistoryDetails,
        },
        stubs: {
          BaseSimpleTable: {
            template: '<div class="mock-table" @row-click="$emit(\'row-click\', $event)"></div>',
            props: ["data", "columns", "options", "loading"],
          },
        },
      });
    });

    it("should display preview content with header information", () => {
      expect(wrapper.find(".preview-content").exists()).toBe(true);
      expect(wrapper.find(".preview-header").exists()).toBe(true);
      expect(wrapper.find(".preview-header h3").text()).toBe("test-papers.csv");
      expect(wrapper.text()).toContain("2 references imported");
    });

    it("should display data table", () => {
      expect(wrapper.find(".table-container").exists()).toBe(true);
      expect(wrapper.find(".mock-table").exists()).toBe(true);
    });

    it("should format date correctly", () => {
      const dateText = wrapper.text();
      expect(dateText).toContain("Jan 15, 2024");
    });

    it("should calculate total records correctly", () => {
      expect(wrapper.vm.totalRecords).toBe(2);
    });

    it("should generate table columns from schema", () => {
      const columns = wrapper.vm.tableColumns;

      expect(columns).toHaveLength(5); // reference + 4 schema fields
      expect(columns[0].field).toBe("reference");
      expect(columns[0].frozen).toBe(true);

      const titleColumn = columns.find((col) => col.field === "title");
      expect(titleColumn).toBeDefined();
      expect(titleColumn.title).toBe("title");
    });

    it("should transform data correctly for table", () => {
      const tableData = wrapper.vm.tableData;

      expect(tableData).toHaveLength(2);
      expect(tableData[0].reference).toBe("paper_001");
      expect(tableData[0].title).toBe("Sample Paper Title 1");
      expect(tableData[0].status).toBe("add");
      expect(tableData[0]._metadata).toEqual({ status: "add" });
    });

    it("should emit row-selected event when row is clicked", async () => {
      const mockRow = { getData: () => ({ reference: "paper_001" }) };
      wrapper.vm.handleRowClick(null, mockRow);

      expect(wrapper.emitted("row-selected")).toBeTruthy();
    });
  });

  describe("Data Filtering", () => {
    beforeEach(() => {
      wrapper = mount(ImportHistoryDataPreview, {
        propsData: {
          loading: false,
          error: null,
          importHistoryDetails: mockImportHistoryDetails,
        },
        stubs: {
          BaseSimpleTable: true,
        },
      });
    });

    it("should filter data by search query", async () => {
      await wrapper.setData({ searchQuery: "Sample Paper Title 1" });

      const filteredData = wrapper.vm.filteredData;
      expect(filteredData).toHaveLength(1);
      expect(filteredData[0].reference).toBe("paper_001");
    });

    it("should filter data by status", async () => {
      // Add a record with different status for testing
      mockImportHistoryDetails.records.push({
        reference: "paper_003",
        title: "Updated Paper",
        status: "update",
      });
      mockImportHistoryDetails.metadata.paper_003 = { status: "update" };

      await wrapper.setData({ statusFilter: "update" });

      const filteredData = wrapper.vm.filteredData;
      expect(filteredData).toHaveLength(1);
      expect(filteredData[0].status).toBe("update");
    });

    it("should reset current page when filters change", async () => {
      await wrapper.setData({ currentPage: 5 });
      await wrapper.setData({ searchQuery: "test" });

      expect(wrapper.vm.currentPage).toBe(1);
    });
  });

  describe("Column Formatters", () => {
    beforeEach(() => {
      wrapper = mount(ImportHistoryDataPreview, {
        propsData: {
          loading: false,
          error: null,
          importHistoryDetails: mockImportHistoryDetails,
        },
        stubs: {
          BaseSimpleTable: true,
        },
      });
    });

    it("should format reference cells correctly", () => {
      const mockCell = { getValue: () => "paper_001" };
      const result = wrapper.vm.referenceFormatter(mockCell);

      expect(result).toBe('<span class="reference-cell">paper_001</span>');
    });

    it("should format boolean cells correctly", () => {
      const mockCell = { getValue: () => true };
      const result = wrapper.vm.booleanFormatter(mockCell);

      expect(result).toContain("boolean-true");
      expect(result).toContain("✓");
    });

    it("should format number cells correctly", () => {
      const mockCell = { getValue: () => 1234 };
      const result = wrapper.vm.numberFormatter(mockCell);

      expect(result).toContain("1,234");
    });

    it("should format URL cells correctly", () => {
      const mockCell = { getValue: () => "https://example.com" };
      const result = wrapper.vm.urlFormatter(mockCell);

      expect(result).toContain('<a href="https://example.com"');
      expect(result).toContain('target="_blank"');
    });

    it("should handle null values in formatters", () => {
      const mockCell = { getValue: () => null };

      expect(wrapper.vm.numberFormatter(mockCell)).toBe("-");
      expect(wrapper.vm.urlFormatter(mockCell)).toBe("-");
    });
  });

  describe("Table Options", () => {
    beforeEach(() => {
      wrapper = mount(ImportHistoryDataPreview, {
        propsData: {
          loading: false,
          error: null,
          importHistoryDetails: mockImportHistoryDetails,
        },
        stubs: {
          BaseSimpleTable: true,
        },
      });
    });

    it("should configure table options correctly", () => {
      const options = wrapper.vm.tableOptions;

      expect(options.layout).toBe("fitDataFill");
      expect(options.maxHeight).toBe("100%");
      expect(options.sortMode).toBe("local");
      expect(options.resizableColumns).toBe(true);
      expect(options.movableColumns).toBe(false);
      expect(options.selectable).toBe(false);
    });

    it("should enable pagination for large datasets", async () => {
      // Add more records to trigger pagination
      const manyRecords = Array.from({ length: 25 }, (_, i) => ({
        reference: `paper_${i.toString().padStart(3, "0")}`,
        title: `Paper Title ${i}`,
      }));

      mockImportHistoryDetails.records = manyRecords;
      await wrapper.vm.$forceUpdate();

      const options = wrapper.vm.tableOptions;
      expect(options.pagination).toBe(true);
    });
  });

  describe("Public Methods", () => {
    beforeEach(() => {
      wrapper = mount(ImportHistoryDataPreview, {
        propsData: {
          loading: false,
          error: null,
          importHistoryDetails: mockImportHistoryDetails,
        },
        stubs: {
          BaseSimpleTable: true,
        },
      });
    });

    it("should clear filters", () => {
      wrapper.setData({
        searchQuery: "test",
        statusFilter: "add",
      });

      wrapper.vm.clearFilters();

      expect(wrapper.vm.searchQuery).toBe("");
      expect(wrapper.vm.statusFilter).toBe("");
    });

    it("should export filtered data", () => {
      const exportedData = wrapper.vm.exportData();

      expect(exportedData).toHaveLength(2);
      expect(exportedData[0].reference).toBe("paper_001");
    });

    it("should get field stats", () => {
      mockImportHistoryDetails.getFieldStats.mockReturnValue({
        unique_count: 2,
        null_count: 0,
      });

      const stats = wrapper.vm.getFieldStats("title");

      expect(mockImportHistoryDetails.getFieldStats).toHaveBeenCalledWith("title");
      expect(stats.unique_count).toBe(2);
    });
  });

  describe("Error Handling", () => {
    it("should handle date formatting errors gracefully", () => {
      mockImportHistoryDetails.createdAt = "invalid-date";

      wrapper = mount(ImportHistoryDataPreview, {
        propsData: {
          loading: false,
          error: null,
          importHistoryDetails: mockImportHistoryDetails,
        },
        stubs: {
          BaseSimpleTable: true,
        },
      });

      // Should not throw error and should show fallback text
      expect(() => wrapper.vm.formatDate("invalid-date")).not.toThrow();
      expect(wrapper.vm.formatDate("invalid-date")).toBe("Invalid date");
    });

    it("should handle missing schema fields gracefully", () => {
      mockImportHistoryDetails.schema = null;

      wrapper = mount(ImportHistoryDataPreview, {
        propsData: {
          loading: false,
          error: null,
          importHistoryDetails: mockImportHistoryDetails,
        },
        stubs: {
          BaseSimpleTable: true,
        },
      });

      expect(wrapper.vm.tableColumns).toEqual([]);
    });

    it("should handle missing records gracefully", () => {
      mockImportHistoryDetails.records = null;

      wrapper = mount(ImportHistoryDataPreview, {
        propsData: {
          loading: false,
          error: null,
          importHistoryDetails: mockImportHistoryDetails,
        },
        stubs: {
          BaseSimpleTable: true,
        },
      });

      expect(wrapper.vm.tableData).toEqual([]);
      expect(wrapper.vm.totalRecords).toBe(0);
    });
  });
});
