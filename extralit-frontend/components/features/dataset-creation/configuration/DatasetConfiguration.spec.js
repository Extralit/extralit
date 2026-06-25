// @vitest-environment nuxt
import { mount } from "@vue/test-utils";
import DatasetConfiguration from "./DatasetConfiguration.vue";
import { ImportHistoryDetails } from "~/v1/domain/entities/import/ImportHistoryDetails";

// Mock dependencies
const mockUseDatasetConfiguration = {
  getFirstRecord: vi.fn(),
  getSuggestedFieldMappings: vi.fn(() => ({})),
  configureImportHistoryFields: vi.fn(),
  getSuggestedQuestions: vi.fn(() => []),
  firstRecord: { reference: "paper_001", title: "Test Paper" },
};

vi.mock("./useDatasetConfiguration", () => ({
  useDatasetConfiguration: vi.fn(() => mockUseDatasetConfiguration),
}));

vi.mock("~/v1/domain/entities/import/ImportHistoryDetails", () => ({
  ImportHistoryDetails: vi.fn(),
}));

describe("DatasetConfiguration", () => {
  let wrapper;
  let mockDataset;
  let mockImportHistoryDetails;

  beforeEach(() => {
    // Reset mocks
    vi.clearAllMocks();

    // Mock dataset object
    mockDataset = {
      repoId: "test-repo",
      mappedFields: { title: "title", reference: "reference" },
      questions: [
        {
          id: "q1",
          name: "quality",
          title: "Quality Assessment",
          type: "rating",
        },
      ],
      createFields: vi.fn(() => [
        { name: "reference", value: "paper_001" },
        { name: "title", value: "Test Paper" },
      ]),
      changeSubset: vi.fn(),
    };

    // Mock ImportHistoryDetails
    mockImportHistoryDetails = {
      filename: "test-papers.csv",
      records: [
        { reference: "paper_001", title: "Test Paper 1" },
        { reference: "paper_002", title: "Test Paper 2" },
      ],
      schema: {
        fields: [
          { name: "reference", type: "string" },
          { name: "title", type: "string" },
        ],
      },
    };

    ImportHistoryDetails.mockImplementation(() => mockImportHistoryDetails);
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
    vi.restoreAllMocks();
  });

  describe("HuggingFace Hub Mode", () => {
    beforeEach(() => {
      wrapper = mount(DatasetConfiguration, {
        props: {
          dataset: mockDataset,
          dataSource: "hub",
        },
        global: { stubs: {
          HorizontalResizable: {
            template: `
              <div class="mock-horizontal-resizable">
                <div class="up-section"><slot name="up" /></div>
                <div class="down-section"><slot name="down" /></div>
              </div>
            `,
            props: ["id", "min-height-percent", "top-percent-height"],
          },
          VerticalResizable: {
            template: `
              <div class="mock-vertical-resizable">
                <div class="left-section"><slot name="left" /></div>
                <div class="right-section"><slot name="right" /></div>
              </div>
            `,
            props: ["id", "left-percent-width"],
          },
          Record: {
            template: '<div class="mock-record">Record Preview</div>',
            props: ["recordCriteria", "record"],
          },
          QuestionsComponent: {
            template: '<div class="mock-questions">Questions</div>',
            props: ["visible-shortcuts", "questions"],
          },
          DatasetConfigurationForm: {
            template: '<div class="mock-config-form">Configuration Form</div>',
            props: ["dataset"],
          },
          ImportHistoryDataPreview: {
            template: '<div class="mock-import-preview">Import Preview</div>',
            props: ["import-history-details", "loading", "error"],
          },
          BaseIcon: true,
        } },
      });
    });

    it("should display HuggingFace iframe for hub data source", () => {
      expect(wrapper.find("iframe").exists()).toBe(true);
      expect(wrapper.find("iframe").attributes("src")).toContain("huggingface.co/datasets/test-repo");
      expect(wrapper.find(".mock-import-preview").exists()).toBe(false);
    });

    it("should display record preview in fields section", () => {
      expect(wrapper.find(".dataset-config__fields .mock-record").exists()).toBe(true);
    });

    it("should display questions in questions section", () => {
      expect(wrapper.find(".mock-questions").exists()).toBe(true);
    });

    it("should display configuration form", () => {
      expect(wrapper.find(".dataset-config__configuration .mock-config-form").exists()).toBe(true);
    });
  });

  describe("ImportHistory Mode", () => {
    beforeEach(() => {
      wrapper = mount(DatasetConfiguration, {
        props: {
          dataset: mockDataset,
          dataSource: "import",
          importData: mockImportHistoryDetails,
        },
        global: { stubs: {
          HorizontalResizable: {
            template: `
              <div class="mock-horizontal-resizable">
                <div class="up-section"><slot name="up" /></div>
                <div class="down-section"><slot name="down" /></div>
              </div>
            `,
            props: ["id", "min-height-percent", "top-percent-height"],
          },
          VerticalResizable: {
            template: `
              <div class="mock-vertical-resizable">
                <div class="left-section"><slot name="left" /></div>
                <div class="right-section"><slot name="right" /></div>
              </div>
            `,
            props: ["id", "left-percent-width"],
          },
          Record: {
            template: '<div class="mock-record">Record Preview</div>',
            props: ["recordCriteria", "record"],
          },
          QuestionsComponent: {
            template: '<div class="mock-questions">Questions</div>',
            props: ["visible-shortcuts", "questions"],
          },
          DatasetConfigurationForm: {
            template: '<div class="mock-config-form">Configuration Form</div>',
            props: ["dataset"],
          },
          ImportHistoryDataPreview: {
            template: '<div class="mock-import-preview">Import Preview</div>',
            props: ["import-history-details", "loading", "error"],
          },
          BaseIcon: true,
        } },
      });
    });

    it("should display ImportHistoryDataPreview for import data source", () => {
      expect(wrapper.find(".mock-import-preview").exists()).toBe(true);
      expect(wrapper.find("iframe").exists()).toBe(false);
    });

    it("should pass correct props to ImportHistoryDataPreview", () => {
      const importPreview = wrapper.find(".mock-import-preview");
      expect(importPreview.exists()).toBe(true);

      // Check that the component receives the import data
      const importPreviewComponent = wrapper.findComponent({ name: "ImportHistoryDataPreview" });
      if (importPreviewComponent.exists()) {
        expect(importPreviewComponent.props("import-history-details")).toBe(mockImportHistoryDetails);
      }
    });

    it("should configure ImportHistory dataset on mount", () => {
      expect(mockUseDatasetConfiguration.getSuggestedFieldMappings).toHaveBeenCalledWith(mockImportHistoryDetails);
      expect(mockUseDatasetConfiguration.configureImportHistoryFields).toHaveBeenCalled();
    });

    it("should emit import-dataset-configured event", () => {
      expect(wrapper.emitted("import-dataset-configured")).toBeTruthy();

      const emittedEvent = wrapper.emitted("import-dataset-configured")[0][0];
      expect(emittedEvent.dataset).toEqual(mockDataset);
      expect(emittedEvent.suggestedMappings).toBeDefined();
      expect(emittedEvent.suggestedQuestions).toBeDefined();
    });
  });

  describe("Empty State", () => {
    beforeEach(() => {
      wrapper = mount(DatasetConfiguration, {
        props: {
          dataset: { ...mockDataset, repoId: null },
          dataSource: "hub",
        },
        global: { stubs: {
          HorizontalResizable: {
            template: `
              <div class="mock-horizontal-resizable">
                <div class="up-section"><slot name="up" /></div>
                <div class="down-section"><slot name="down" /></div>
              </div>
            `,
          },
          VerticalResizable: {
            template: `
              <div class="mock-vertical-resizable">
                <div class="left-section"><slot name="left" /></div>
                <div class="right-section"><slot name="right" /></div>
              </div>
            `,
          },
          Record: true,
          QuestionsComponent: true,
          DatasetConfigurationForm: true,
          ImportHistoryDataPreview: true,
          BaseIcon: {
            template: '<div class="mock-icon"></div>',
            props: ["icon-name"],
          },
        } },
      });
    });

    it("should display placeholder when no data is available", () => {
      expect(wrapper.find(".dataset-config__preview-placeholder").exists()).toBe(true);
      expect(wrapper.text()).toContain("No preview data available");
    });
  });

  describe("Questions Display", () => {
    it("should display empty questions message when no questions", () => {
      const datasetWithoutQuestions = { ...mockDataset, questions: [] };

      wrapper = mount(DatasetConfiguration, {
        props: {
          dataset: datasetWithoutQuestions,
          dataSource: "hub",
        },
        global: { stubs: {
          HorizontalResizable: {
            template: `
              <div class="mock-horizontal-resizable">
                <div class="up-section"><slot name="up" /></div>
                <div class="down-section"><slot name="down" /></div>
              </div>
            `,
          },
          VerticalResizable: {
            template: `
              <div class="mock-vertical-resizable">
                <div class="left-section"><slot name="left" /></div>
                <div class="right-section"><slot name="right" /></div>
              </div>
            `,
          },
          Record: true,
          QuestionsComponent: true,
          DatasetConfigurationForm: true,
          ImportHistoryDataPreview: true,
          BaseIcon: true,
        } },
      });

      expect(wrapper.find(".dataset-config__empty-questions").exists()).toBe(true);
      expect(wrapper.text()).toContain("#datasetCreation.yourQuestions#");
    });

    it("should display questions component when questions exist", () => {
      wrapper = mount(DatasetConfiguration, {
        props: {
          dataset: mockDataset,
          dataSource: "hub",
        },
        global: { stubs: {
          HorizontalResizable: {
            template: `
              <div class="mock-horizontal-resizable">
                <div class="up-section"><slot name="up" /></div>
                <div class="down-section"><slot name="down" /></div>
              </div>
            `,
          },
          VerticalResizable: {
            template: `
              <div class="mock-vertical-resizable">
                <div class="left-section"><slot name="left" /></div>
                <div class="right-section"><slot name="right" /></div>
              </div>
            `,
          },
          Record: true,
          QuestionsComponent: {
            template: '<div class="mock-questions">Questions Component</div>',
            props: ["visible-shortcuts", "questions"],
          },
          DatasetConfigurationForm: true,
          ImportHistoryDataPreview: true,
          BaseIcon: true,
        } },
      });

      expect(wrapper.find(".mock-questions").exists()).toBe(true);
      expect(wrapper.find(".dataset-config__empty-questions").exists()).toBe(false);
    });
  });

  describe("Event Handling", () => {
    beforeEach(() => {
      wrapper = mount(DatasetConfiguration, {
        props: {
          dataset: mockDataset,
          dataSource: "import",
          importData: mockImportHistoryDetails,
        },
        global: { stubs: {
          HorizontalResizable: {
            template: `
              <div class="mock-horizontal-resizable">
                <div class="up-section"><slot name="up" /></div>
                <div class="down-section"><slot name="down" /></div>
              </div>
            `,
          },
          VerticalResizable: {
            template: `
              <div class="mock-vertical-resizable">
                <div class="left-section"><slot name="left" /></div>
                <div class="right-section"><slot name="right" /></div>
              </div>
            `,
          },
          Record: true,
          QuestionsComponent: true,
          DatasetConfigurationForm: {
            template:
              "<div class=\"mock-config-form\" @change-subset=\"$emit('change-subset', 'test-subset')\">Configuration Form</div>",
            props: ["dataset"],
          },
          ImportHistoryDataPreview: {
            template: `
              <div class="mock-import-preview"
                   @retry="$emit('retry')"
                   @row-selected="$emit('row-selected', { reference: 'paper_001' })"
                   @field-selected="$emit('field-selected', { name: 'title' })">
                Import Preview
              </div>
            `,
            props: ["import-history-details", "loading", "error"],
          },
          BaseIcon: true,
        } },
      });
    });

    it("should emit change-subset event from configuration form", async () => {
      const configForm = wrapper.find(".mock-config-form");
      await configForm.trigger("change-subset");

      expect(wrapper.emitted("change-subset")).toBeTruthy();
      expect(wrapper.emitted("change-subset")[0]).toEqual(["test-subset"]);
    });

    it("should emit retry-import-data event from import preview", async () => {
      const importPreview = wrapper.find(".mock-import-preview");
      await importPreview.trigger("retry");

      expect(wrapper.emitted("retry-import-data")).toBeTruthy();
    });

    it("should emit import-row-selected event from import preview", async () => {
      const importPreview = wrapper.find(".mock-import-preview");
      await importPreview.trigger("row-selected");

      expect(wrapper.emitted("import-row-selected")).toBeTruthy();
      expect(wrapper.emitted("import-row-selected")[0]).toEqual([{ reference: "paper_001" }]);
    });

    it("should emit import-field-selected event from import preview", async () => {
      const importPreview = wrapper.find(".mock-import-preview");
      await importPreview.trigger("field-selected");

      expect(wrapper.emitted("import-field-selected")).toBeTruthy();
      expect(wrapper.emitted("import-field-selected")[0]).toEqual([{ name: "title" }]);
    });
  });

  describe("Watchers", () => {
    beforeEach(() => {
      wrapper = mount(DatasetConfiguration, {
        props: {
          dataset: mockDataset,
          dataSource: "import",
          importData: mockImportHistoryDetails,
        },
        global: { stubs: {
          HorizontalResizable: {
            template: `<div><slot name="up" /><slot name="down" /></div>`,
          },
          VerticalResizable: {
            template: `<div><slot name="left" /><slot name="right" /></div>`,
          },
          Record: true,
          QuestionsComponent: true,
          DatasetConfigurationForm: true,
          ImportHistoryDataPreview: true,
          BaseIcon: true,
        } },
      });
    });

    it("should reconfigure when dataset changes", async () => {
      // Reset mock calls
      mockUseDatasetConfiguration.getFirstRecord.mockClear();

      const newDataset = { ...mockDataset, name: "Updated Dataset" };
      await wrapper.setProps({ dataset: newDataset });

      expect(mockUseDatasetConfiguration.getFirstRecord).toHaveBeenCalledWith(
        newDataset,
        "import",
        mockImportHistoryDetails
      );
    });

    it("should reconfigure when importData changes", async () => {
      // Reset mock calls
      mockUseDatasetConfiguration.getFirstRecord.mockClear();
      mockUseDatasetConfiguration.configureImportHistoryFields.mockClear();

      const newImportData = { ...mockImportHistoryDetails, filename: "new-file.csv" };
      await wrapper.setProps({ importData: newImportData });

      expect(mockUseDatasetConfiguration.getFirstRecord).toHaveBeenCalledWith(mockDataset, "import", newImportData);
      expect(mockUseDatasetConfiguration.configureImportHistoryFields).toHaveBeenCalled();
    });

    it("should reconfigure when dataSource changes", async () => {
      // Reset mock calls
      mockUseDatasetConfiguration.getFirstRecord.mockClear();

      await wrapper.setProps({ dataSource: "hub" });

      expect(mockUseDatasetConfiguration.getFirstRecord).toHaveBeenCalledWith(
        mockDataset,
        "hub",
        mockImportHistoryDetails
      );
    });
  });

  describe("Error Handling", () => {
    it("should handle configuration errors gracefully", () => {
      // Mock configuration to throw error
      mockUseDatasetConfiguration.configureImportHistoryFields.mockImplementation(() => {
        throw new Error("Configuration failed");
      });

      // Mock console.error to avoid noise in tests
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

      // Should not throw error when mounting
      expect(() => {
        wrapper = mount(DatasetConfiguration, {
          props: {
            dataset: mockDataset,
            dataSource: "import",
            importData: mockImportHistoryDetails,
          },
          global: { stubs: {
            HorizontalResizable: { template: `<div><slot name="up" /><slot name="down" /></div>` },
            VerticalResizable: { template: `<div><slot name="left" /><slot name="right" /></div>` },
            Record: true,
            QuestionsComponent: true,
            DatasetConfigurationForm: true,
            ImportHistoryDataPreview: true,
            BaseIcon: true,
          } },
        });
      }).not.toThrow();

      expect(consoleSpy).toHaveBeenCalledWith("Error configuring ImportHistory dataset:", expect.any(Error));

      consoleSpy.mockRestore();
    });
  });

  describe("Props Validation", () => {
    it("should validate dataSource prop", () => {
      const validator = DatasetConfiguration.props.dataSource.validator;

      expect(validator("hub")).toBe(true);
      expect(validator("import")).toBe(true);
      expect(validator("invalid")).toBe(false);
    });

    it("should have correct default values", () => {
      expect(DatasetConfiguration.props.dataSource.default).toBe("hub");
      expect(DatasetConfiguration.props.importData.default).toBeNull();
      expect(DatasetConfiguration.props.isLoadingImportData.default).toBe(false);
      expect(DatasetConfiguration.props.importDataError.default).toBeNull();
    });
  });
});
