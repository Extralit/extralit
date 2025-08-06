/**
 * Test suite for RecentImportCard component
 * Tests card display, interaction, date formatting, and responsive design
 */

import { mount } from "@vue/test-utils";
import RecentImportCard from "./RecentImportCard.vue";

// Mock assets
jest.mock("assets/icons/time", () => ({}));

describe("RecentImportCard Component", () => {
  let wrapper;

  const mockImportRecord = {
    id: "import-1",
    filename: "test-bibliography.bib",
    created_at: "2025-01-01T10:00:00Z",
    total_papers: 15,
    success_count: 12,
    failed_count: 3,
  };

  const mockImportRecordNoFailures = {
    id: "import-2",
    filename: "successful-import.bib",
    created_at: "2025-01-02T15:30:00Z",
    total_papers: 8,
    success_count: 8,
    failed_count: 0,
  };

  beforeEach(() => {
    // Mock Date.now() for consistent date formatting tests
    jest.spyOn(Date, "now").mockImplementation(() => new Date("2025-01-01T12:00:00Z").getTime());
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.destroy();
    }
    jest.restoreAllMocks();
  });

  describe("Component Structure and Display", () => {
    it("should render the component with correct structure", () => {
      wrapper = mount(RecentImportCard, {
        propsData: { importRecord: mockImportRecord },
        stubs: {
          BaseButton: {
            template: '<button class="mock-base-button"><slot /></button>',
          },
          BaseIcon: {
            template: '<div class="mock-icon"></div>',
            props: ["iconName"],
          },
        },
      });

      expect(wrapper.find(".recent-import-card").exists()).toBe(true);
      expect(wrapper.find(".recent-import-card__content").exists()).toBe(true);
      expect(wrapper.find(".recent-import-card__header").exists()).toBe(true);
      expect(wrapper.find(".recent-import-card__stats").exists()).toBe(true);
    });

    it("should display filename correctly", () => {
      wrapper = mount(RecentImportCard, {
        propsData: { importRecord: mockImportRecord },
        stubs: {
          BaseButton: {
            template: '<button class="mock-base-button"><slot /></button>',
          },
          BaseIcon: {
            template: '<div class="mock-icon"></div>',
            props: ["iconName"],
          },
        },
      });

      const filename = wrapper.find(".recent-import-card__filename");
      expect(filename.text()).toBe("test-bibliography.bib");
    });

    it("should display statistics correctly", () => {
      wrapper = mount(RecentImportCard, {
        propsData: { importRecord: mockImportRecord },
        stubs: {
          BaseButton: {
            template: '<button class="mock-base-button"><slot /></button>',
          },
          BaseIcon: {
            template: '<div class="mock-icon"></div>',
            props: ["iconName"],
          },
        },
      });

      const stats = wrapper.findAll(".recent-import-card__stat");
      expect(stats).toHaveLength(3); // papers, success, failed

      // Check papers stat
      const papersCount = stats.at(0).find(".recent-import-card__stat-count");
      const papersLabel = stats.at(0).find(".recent-import-card__stat-label");
      expect(papersCount.text()).toBe("15");
      expect(papersLabel.text()).toBe("papers");

      // Check success stat
      const successCount = stats.at(1).find(".recent-import-card__stat-count");
      const successLabel = stats.at(1).find(".recent-import-card__stat-label");
      expect(successCount.text()).toBe("12");
      expect(successLabel.text()).toBe("success");

      // Check failed stat
      const failedCount = stats.at(2).find(".recent-import-card__stat-count");
      const failedLabel = stats.at(2).find(".recent-import-card__stat-label");
      expect(failedCount.text()).toBe("3");
      expect(failedLabel.text()).toBe("failed");
    });

    it("should not display failed stat when failed_count is 0", () => {
      wrapper = mount(RecentImportCard, {
        propsData: { importRecord: mockImportRecordNoFailures },
        stubs: {
          BaseButton: {
            template: '<button class="mock-base-button"><slot /></button>',
          },
          BaseIcon: {
            template: '<div class="mock-icon"></div>',
            props: ["iconName"],
          },
        },
      });

      const stats = wrapper.findAll(".recent-import-card__stat");
      expect(stats).toHaveLength(2); // only papers and success

      const failedStat = wrapper.find(".recent-import-card__stat--failed");
      expect(failedStat.exists()).toBe(false);
    });
  });

  describe("Date Formatting", () => {
    it("should format recent dates as 'Just now'", () => {
      const recentRecord = {
        ...mockImportRecord,
        created_at: "2025-01-01T11:59:00Z", // 1 minute ago
      };

      wrapper = mount(RecentImportCard, {
        propsData: { importRecord: recentRecord },
        stubs: {
          BaseButton: {
            template: '<button class="mock-base-button"><slot /></button>',
          },
          BaseIcon: {
            template: '<div class="mock-icon"></div>',
            props: ["iconName"],
          },
        },
      });

      const dateElement = wrapper.find(".recent-import-card__date");
      expect(dateElement.text()).toContain("Just now");
    });

    it("should format dates within 24 hours as hours ago", () => {
      const hoursAgoRecord = {
        ...mockImportRecord,
        created_at: "2025-01-01T08:00:00Z", // 4 hours ago
      };

      wrapper = mount(RecentImportCard, {
        propsData: { importRecord: hoursAgoRecord },
        stubs: {
          BaseButton: {
            template: '<button class="mock-base-button"><slot /></button>',
          },
          BaseIcon: {
            template: '<div class="mock-icon"></div>',
            props: ["iconName"],
          },
        },
      });

      const dateElement = wrapper.find(".recent-import-card__date");
      expect(dateElement.text()).toContain("4h ago");
    });

    it("should format yesterday dates as 'Yesterday'", () => {
      const yesterdayRecord = {
        ...mockImportRecord,
        created_at: "2024-12-31T12:00:00Z", // Yesterday
      };

      wrapper = mount(RecentImportCard, {
        propsData: { importRecord: yesterdayRecord },
        stubs: {
          BaseButton: {
            template: '<button class="mock-base-button"><slot /></button>',
          },
          BaseIcon: {
            template: '<div class="mock-icon"></div>',
            props: ["iconName"],
          },
        },
      });

      const dateElement = wrapper.find(".recent-import-card__date");
      expect(dateElement.text()).toContain("Yesterday");
    });

    it("should format dates within a week as days ago", () => {
      const daysAgoRecord = {
        ...mockImportRecord,
        created_at: "2024-12-29T12:00:00Z", // 3 days ago
      };

      wrapper = mount(RecentImportCard, {
        propsData: { importRecord: daysAgoRecord },
        stubs: {
          BaseButton: {
            template: '<button class="mock-base-button"><slot /></button>',
          },
          BaseIcon: {
            template: '<div class="mock-icon"></div>',
            props: ["iconName"],
          },
        },
      });

      const dateElement = wrapper.find(".recent-import-card__date");
      expect(dateElement.text()).toContain("3d ago");
    });

    it("should format older dates as locale date string", () => {
      const oldRecord = {
        ...mockImportRecord,
        created_at: "2024-12-01T12:00:00Z", // More than a week ago
      };

      wrapper = mount(RecentImportCard, {
        propsData: { importRecord: oldRecord },
        stubs: {
          BaseButton: {
            template: '<button class="mock-base-button"><slot /></button>',
          },
          BaseIcon: {
            template: '<div class="mock-icon"></div>',
            props: ["iconName"],
          },
        },
      });

      const dateElement = wrapper.find(".recent-import-card__date");
      // Should contain a formatted date string
      expect(dateElement.text()).toMatch(/\d{1,2}\/\d{1,2}\/\d{4}/);
    });

    it("should handle invalid dates gracefully", () => {
      const invalidDateRecord = {
        ...mockImportRecord,
        created_at: "invalid-date",
      };

      wrapper = mount(RecentImportCard, {
        propsData: { importRecord: invalidDateRecord },
        stubs: {
          BaseButton: {
            template: '<button class="mock-base-button"><slot /></button>',
          },
          BaseIcon: {
            template: '<div class="mock-icon"></div>',
            props: ["iconName"],
          },
        },
      });

      const dateElement = wrapper.find(".recent-import-card__date");
      expect(dateElement.text()).toContain("Unknown");
    });
  });

  describe("Event Handling", () => {
    it("should emit click event when card is clicked", async () => {
      wrapper = mount(RecentImportCard, {
        propsData: { importRecord: mockImportRecord },
        stubs: {
          BaseButton: {
            template: '<button class="mock-base-button" @click="$emit(\'click\')"><slot /></button>',
          },
          BaseIcon: {
            template: '<div class="mock-icon"></div>',
            props: ["iconName"],
          },
        },
      });

      const button = wrapper.find(".mock-base-button");
      await button.trigger("click");

      expect(wrapper.emitted("click")).toBeTruthy();
      expect(wrapper.emitted("click")).toHaveLength(1);
    });
  });

  describe("Computed Properties", () => {
    it("should calculate totalPapers correctly", () => {
      wrapper = mount(RecentImportCard, {
        propsData: { importRecord: mockImportRecord },
        stubs: {
          BaseButton: {
            template: '<button class="mock-base-button"><slot /></button>',
          },
          BaseIcon: {
            template: '<div class="mock-icon"></div>',
            props: ["iconName"],
          },
        },
      });

      expect(wrapper.vm.totalPapers).toBe(15);
    });

    it("should handle missing total_papers gracefully", () => {
      const recordWithoutTotal = {
        ...mockImportRecord,
        total_papers: undefined,
      };

      wrapper = mount(RecentImportCard, {
        propsData: { importRecord: recordWithoutTotal },
        stubs: {
          BaseButton: {
            template: '<button class="mock-base-button"><slot /></button>',
          },
          BaseIcon: {
            template: '<div class="mock-icon"></div>',
            props: ["iconName"],
          },
        },
      });

      expect(wrapper.vm.totalPapers).toBe(0);
    });
  });

  describe("Styling and CSS Classes", () => {
    it("should apply correct CSS classes", () => {
      wrapper = mount(RecentImportCard, {
        propsData: { importRecord: mockImportRecord },
        stubs: {
          BaseButton: {
            template: '<button class="mock-base-button recent-import-card"><slot /></button>',
          },
          BaseIcon: {
            template: '<div class="mock-icon"></div>',
            props: ["iconName"],
          },
        },
      });

      expect(wrapper.find(".recent-import-card").exists()).toBe(true);
      expect(wrapper.find(".recent-import-card__content").exists()).toBe(true);
      expect(wrapper.find(".recent-import-card__header").exists()).toBe(true);
      expect(wrapper.find(".recent-import-card__filename").exists()).toBe(true);
      expect(wrapper.find(".recent-import-card__date").exists()).toBe(true);
      expect(wrapper.find(".recent-import-card__stats").exists()).toBe(true);
    });

    it("should apply success styling to success stat", () => {
      wrapper = mount(RecentImportCard, {
        propsData: { importRecord: mockImportRecord },
        stubs: {
          BaseButton: {
            template: '<button class="mock-base-button"><slot /></button>',
          },
          BaseIcon: {
            template: '<div class="mock-icon"></div>',
            props: ["iconName"],
          },
        },
      });

      const successStat = wrapper.find(".recent-import-card__stat--success");
      expect(successStat.exists()).toBe(true);
    });

    it("should apply failed styling to failed stat when failures exist", () => {
      wrapper = mount(RecentImportCard, {
        propsData: { importRecord: mockImportRecord },
        stubs: {
          BaseButton: {
            template: '<button class="mock-base-button"><slot /></button>',
          },
          BaseIcon: {
            template: '<div class="mock-icon"></div>',
            props: ["iconName"],
          },
        },
      });

      const failedStat = wrapper.find(".recent-import-card__stat--failed");
      expect(failedStat.exists()).toBe(true);
    });
  });

  describe("Responsive Design", () => {
    it("should have responsive structure for different screen sizes", () => {
      wrapper = mount(RecentImportCard, {
        propsData: { importRecord: mockImportRecord },
        stubs: {
          BaseButton: {
            template: '<button class="mock-base-button"><slot /></button>',
          },
          BaseIcon: {
            template: '<div class="mock-icon"></div>',
            props: ["iconName"],
          },
        },
      });

      // Verify that elements that need responsive behavior are present
      expect(wrapper.find(".recent-import-card__filename").exists()).toBe(true);
      expect(wrapper.find(".recent-import-card__date").exists()).toBe(true);
      expect(wrapper.find(".recent-import-card__stats").exists()).toBe(true);
    });
  });

  describe("Accessibility", () => {
    it("should have proper heading structure", () => {
      wrapper = mount(RecentImportCard, {
        propsData: { importRecord: mockImportRecord },
        stubs: {
          BaseButton: {
            template: '<button class="mock-base-button"><slot /></button>',
          },
          BaseIcon: {
            template: '<div class="mock-icon"></div>',
            props: ["iconName"],
          },
        },
      });

      const filename = wrapper.find(".recent-import-card__filename");
      expect(filename.element.tagName).toBe("H4");
    });

    it("should provide meaningful text content", () => {
      wrapper = mount(RecentImportCard, {
        propsData: { importRecord: mockImportRecord },
        stubs: {
          BaseButton: {
            template: '<button class="mock-base-button"><slot /></button>',
          },
          BaseIcon: {
            template: '<div class="mock-icon"></div>',
            props: ["iconName"],
          },
        },
      });

      // Check that all text content is meaningful
      expect(wrapper.text()).toContain("test-bibliography.bib");
      expect(wrapper.text()).toContain("15");
      expect(wrapper.text()).toContain("papers");
      expect(wrapper.text()).toContain("12");
      expect(wrapper.text()).toContain("success");
      expect(wrapper.text()).toContain("3");
      expect(wrapper.text()).toContain("failed");
    });
  });

  describe("Long Filename Handling", () => {
    it("should handle very long filenames", () => {
      const longFilenameRecord = {
        ...mockImportRecord,
        filename: "this-is-a-very-long-filename-that-should-be-truncated-properly-in-the-ui.bib",
      };

      wrapper = mount(RecentImportCard, {
        propsData: { importRecord: longFilenameRecord },
        stubs: {
          BaseButton: {
            template: '<button class="mock-base-button"><slot /></button>',
          },
          BaseIcon: {
            template: '<div class="mock-icon"></div>',
            props: ["iconName"],
          },
        },
      });

      const filename = wrapper.find(".recent-import-card__filename");
      expect(filename.text()).toBe(longFilenameRecord.filename);
      // The CSS should handle truncation, so we just verify the content is there
    });
  });
});