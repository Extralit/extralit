import { mount } from "@vue/test-utils";
import ImportSummary from "./ImportSummary.vue";

// Mock base components (.vue modules expose the component as the default export)
vi.mock("~/components/base/base-icon/BaseIcon.vue", () => ({
  default: {
    name: "BaseIcon",
    template: "<span>{{ iconName }}</span>",
    props: ["iconName"],
  },
}));

vi.mock("~/components/base/base-button/BaseButton.vue", () => ({
  default: {
    name: "BaseButton",
    template: "<button><slot></slot></button>",
    props: ["variant", "disabled"],
  },
}));

vi.mock("~/components/base/base-simple-table/BaseSimpleTable.vue", () => ({
  default: {
    name: "BaseSimpleTable",
    template: "<div>Table</div>",
    props: ["data", "columns", "options"],
  },
}));

describe("ImportSummary", () => {
  let wrapper;

  const mockWorkspace = {
    id: "workspace-1",
    name: "Test Workspace",
  };

  const createWrapper = (importSummary = {}, props = {}) => {
    const defaultImportSummary = {
      total: 0,
      added: 0,
      updated: 0,
      skipped: 0,
      failed: 0,
      errors: [],
      importId: "test-import-123",
      ...importSummary,
    };

    return mount(ImportSummary, {
      props: {
        importSummary: defaultImportSummary,
        workspace: mockWorkspace,
        bibFileName: "test.bib",
        failedDocuments: [],
        ...props,
      },
    });
  };

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
  });

  describe("Zero-safe rendering", () => {
    it("displays 0 for all stats when summary data is empty", () => {
      wrapper = createWrapper();

      // Check all stat cards display 0
      const statCards = wrapper.findAll(".stat-card");
      expect(statCards.length).toBe(5); // total, added, updated, skipped, failed

      // Check specific values
      expect(wrapper.find(".stat-total .stat-value").text()).toBe("0");
      expect(wrapper.find(".stat-added .stat-value").text()).toBe("0");
      expect(wrapper.find(".stat-updated .stat-value").text()).toBe("0");
      expect(wrapper.find(".stat-skipped .stat-value").text()).toBe("0");
      expect(wrapper.find(".stat-failed .stat-value").text()).toBe("0");
    });

    it("displays 0 for missing properties in summary data", () => {
      wrapper = createWrapper({
        total: 10,
        added: 5,
        // updated, skipped, failed are missing
        errors: [],
        importId: "test-123",
      });

      expect(wrapper.find(".stat-total .stat-value").text()).toBe("10");
      expect(wrapper.find(".stat-added .stat-value").text()).toBe("5");
      expect(wrapper.find(".stat-updated .stat-value").text()).toBe("0");
      expect(wrapper.find(".stat-skipped .stat-value").text()).toBe("0");
      expect(wrapper.find(".stat-failed .stat-value").text()).toBe("0");
    });

    it("displays 0 for null/undefined values", () => {
      wrapper = createWrapper({
        total: null,
        added: undefined,
        updated: null,
        skipped: undefined,
        failed: null,
        errors: [],
        importId: "test-123",
      });

      expect(wrapper.find(".stat-total .stat-value").text()).toBe("0");
      expect(wrapper.find(".stat-added .stat-value").text()).toBe("0");
      expect(wrapper.find(".stat-updated .stat-value").text()).toBe("0");
      expect(wrapper.find(".stat-skipped .stat-value").text()).toBe("0");
      expect(wrapper.find(".stat-failed .stat-value").text()).toBe("0");
    });
  });

  describe("Accurate count display", () => {
    it("displays correct counts for mixed summary", () => {
      wrapper = createWrapper({
        total: 100,
        added: 60,
        updated: 25,
        skipped: 10,
        failed: 5,
        errors: [
          { reference: "ref1", message: "error1" },
          { reference: "ref2", message: "error2" },
        ],
        importId: "test-123",
      });

      expect(wrapper.find(".stat-total .stat-value").text()).toBe("100");
      expect(wrapper.find(".stat-added .stat-value").text()).toBe("60");
      expect(wrapper.find(".stat-updated .stat-value").text()).toBe("25");
      expect(wrapper.find(".stat-skipped .stat-value").text()).toBe("10");
      expect(wrapper.find(".stat-failed .stat-value").text()).toBe("5");
    });

    it("computes successful count correctly", () => {
      wrapper = createWrapper({
        total: 100,
        added: 40,
        updated: 35,
        skipped: 15,
        failed: 10,
        errors: [],
        importId: "test-123",
      });

      expect(wrapper.vm.successfulCount).toBe(75); // 40 + 35
    });

    it("computes successful count with zero-safe values", () => {
      wrapper = createWrapper({
        total: 50,
        added: null,
        updated: undefined,
        skipped: 10,
        failed: 5,
        errors: [],
        importId: "test-123",
      });

      expect(wrapper.vm.successfulCount).toBe(0); // 0 + 0
    });
  });

  describe("Failed imports section", () => {
    it("shows failed section when failed count > 0", () => {
      wrapper = createWrapper({
        total: 10,
        added: 5,
        updated: 2,
        skipped: 1,
        failed: 2,
        errors: [
          { reference: "ref1", message: "error1" },
          { reference: "ref2", message: "error2" },
        ],
        importId: "test-123",
      });

      const failedSection = wrapper.find(".failed-section");
      expect(failedSection.exists()).toBe(true);
      expect(failedSection.find(".section-count").text()).toBe("2");
    });

    it("hides failed section when failed count is 0", () => {
      wrapper = createWrapper({
        total: 10,
        added: 7,
        updated: 2,
        skipped: 1,
        failed: 0,
        errors: [],
        importId: "test-123",
      });

      const failedSection = wrapper.find(".failed-section");
      expect(failedSection.exists()).toBe(false);
    });

    it("shows failed imports table when there are failed documents", () => {
      const failedDocs = [
        {
          reference: "ref1",
          title: "Test Paper 1",
          authors: ["Author 1"],
          error: "Upload failed",
        },
      ];

      wrapper = createWrapper(
        {
          total: 10,
          added: 8,
          updated: 1,
          skipped: 0,
          failed: 1,
          errors: [{ reference: "ref1", message: "Upload failed" }],
          importId: "test-123",
        },
        { failedDocuments: failedDocs }
      );

      expect(wrapper.vm.hasFailedImports).toBe(true);
      const failedTable = wrapper.find(".failed-imports");
      expect(failedTable.exists()).toBe(true);
    });
  });

  describe("Skipped section", () => {
    it("shows skipped section when skipped count > 0", () => {
      wrapper = createWrapper({
        total: 10,
        added: 5,
        updated: 2,
        skipped: 3,
        failed: 0,
        errors: [],
        importId: "test-123",
      });

      const skippedSection = wrapper.find(".skipped-section");
      expect(skippedSection.exists()).toBe(true);
      expect(skippedSection.find(".section-count").text()).toBe("3");
    });

    it("hides skipped section when skipped count is 0", () => {
      wrapper = createWrapper({
        total: 10,
        added: 7,
        updated: 3,
        skipped: 0,
        failed: 0,
        errors: [],
        importId: "test-123",
      });

      const skippedSection = wrapper.find(".skipped-section");
      expect(skippedSection.exists()).toBe(false);
    });
  });

  describe("Success section", () => {
    it("shows success section when there are successful imports", () => {
      wrapper = createWrapper({
        total: 10,
        added: 5,
        updated: 3,
        skipped: 1,
        failed: 1,
        errors: [],
        importId: "test-123",
      });

      const successSection = wrapper.find(".success-section");
      expect(successSection.exists()).toBe(true);
      expect(successSection.find(".section-count").text()).toBe("8"); // 5 + 3
    });

    it("hides success section when no successful imports", () => {
      wrapper = createWrapper({
        total: 10,
        added: 0,
        updated: 0,
        skipped: 5,
        failed: 5,
        errors: [],
        importId: "test-123",
      });

      const successSection = wrapper.find(".success-section");
      expect(successSection.exists()).toBe(false);
    });
  });

  describe("Event emissions", () => {
    it("emits return-to-library event", async () => {
      wrapper = createWrapper();

      const returnButton = wrapper.find(".primary-action");
      await returnButton.trigger("click");

      expect(wrapper.emitted("return-to-library")).toBeTruthy();
      expect(wrapper.emitted("return-to-library")[0]).toEqual([{ workspace: mockWorkspace }]);
    });

    it("emits view-import-history event", async () => {
      wrapper = createWrapper({
        total: 5,
        added: 3,
        updated: 1,
        skipped: 1,
        failed: 0,
        errors: [],
        importId: "test-import-123",
      });

      const logButton = wrapper.find(".action-button:not(.primary-action)");
      await logButton.trigger("click");

      expect(wrapper.emitted("view-import-history")).toBeTruthy();
      expect(wrapper.emitted("view-import-history")[0]).toEqual([
        { importId: "test-import-123", workspace: mockWorkspace },
      ]);
    });
  });

  describe("Edge cases", () => {
    it("handles all-zero summary correctly", () => {
      wrapper = createWrapper({
        total: 0,
        added: 0,
        updated: 0,
        skipped: 0,
        failed: 0,
        errors: [],
        importId: "test-123",
      });

      // All stat values should be 0
      expect(wrapper.find(".stat-total .stat-value").text()).toBe("0");
      expect(wrapper.find(".stat-added .stat-value").text()).toBe("0");
      expect(wrapper.find(".stat-updated .stat-value").text()).toBe("0");
      expect(wrapper.find(".stat-skipped .stat-value").text()).toBe("0");
      expect(wrapper.find(".stat-failed .stat-value").text()).toBe("0");

      // No breakdown sections should show
      expect(wrapper.find(".success-section").exists()).toBe(false);
      expect(wrapper.find(".skipped-section").exists()).toBe(false);
      expect(wrapper.find(".failed-section").exists()).toBe(false);
    });

    it("handles failure-heavy summary correctly", () => {
      wrapper = createWrapper({
        total: 10,
        added: 1,
        updated: 0,
        skipped: 1,
        failed: 8,
        errors: [
          { reference: "ref1", message: "error" },
          { reference: "ref2", message: "error" },
          { reference: "ref3", message: "error" },
        ],
        importId: "test-123",
      });

      expect(wrapper.find(".stat-failed .stat-value").text()).toBe("8");
      expect(wrapper.find(".failed-section").exists()).toBe(true);
      expect(wrapper.find(".success-section").exists()).toBe(true); // 1 successful
    });
  });
});
