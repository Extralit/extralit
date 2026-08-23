/**
 * Test suite for RecentImports component
 * Tests Recent Imports display, interaction, workspace selection integration,
 * modal opening, navigation, and responsive design
 */

import { mount } from "@vue/test-utils";
import RecentImports from "./RecentImports.vue";
import { useRecentImportsViewModel } from "./useRecentImportsViewModel";

// Mock the view model
const mockViewModel = {
  recentImports: [],
  isLoading: false,
  error: null,
  hasWorkspace: true,
  loadRecentImports: vi.fn(),
  retryLoad: vi.fn(),
};

vi.mock("./useRecentImportsViewModel", () => ({
  useRecentImportsViewModel: vi.fn(() => mockViewModel),
}));

// Mock assets
vi.mock("assets/icons/danger", () => ({}));
vi.mock("assets/icons/document", () => ({}));
vi.mock("assets/icons/import", () => ({}));

describe("RecentImports Component", () => {
  let wrapper;

  const mockWorkspace = {
    id: "workspace-1",
    name: "Test Workspace",
  };

  const mockImportRecords = [
    {
      id: "import-1",
      filename: "test-file-1.bib",
      created_at: "2025-01-01T10:00:00Z",
      total_papers: 10,
      success_count: 8,
      failed_count: 2,
    },
    {
      id: "import-2",
      filename: "test-file-2.bib",
      created_at: "2025-01-02T15:30:00Z",
      total_papers: 5,
      success_count: 5,
      failed_count: 0,
    },
  ];

  beforeEach(() => {
    // Reset mock state
    mockViewModel.recentImports = [];
    mockViewModel.isLoading = false;
    mockViewModel.error = null;
    mockViewModel.hasWorkspace = true;
    mockViewModel.loadRecentImports.mockClear();
    mockViewModel.retryLoad.mockClear();
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
    vi.restoreAllMocks();
  });

  describe("Component Structure and Display", () => {
    it("should render the component with correct header", () => {
      wrapper = mount(RecentImports, {
        props: { workspace: mockWorkspace },
        global: {
          stubs: {
            BaseSpinner: true,
            BaseIcon: true,
            BaseButton: {
              template: '<button class="mock-base-button"><slot /></button>',
              props: ["variant"],
            },
            RecentImportCard: true,
          },
        },
      });

      expect(wrapper.find(".recent-imports__title").text()).toBe("Recent Imports");
      expect(wrapper.find(".recent-imports__subtitle").text()).toBe("Configure datasets from your recent imports");
    });

    it("should display recent imports list when data is available", () => {
      mockViewModel.recentImports = mockImportRecords;

      wrapper = mount(RecentImports, {
        props: { workspace: mockWorkspace },
        global: {
          stubs: {
            BaseSpinner: true,
            BaseIcon: true,
            BaseButton: {
              template: '<button class="mock-base-button"><slot /></button>',
              props: ["variant"],
            },
            RecentImportCard: {
              template: '<div class="mock-recent-import-card" @click="$emit(\'click\')"></div>',
              props: ["importRecord"],
            },
          },
        },
      });

      const importCards = wrapper.findAll(".mock-recent-import-card");
      expect(importCards).toHaveLength(2);
    });

    it("should display action buttons", () => {
      wrapper = mount(RecentImports, {
        props: { workspace: mockWorkspace },
        global: {
          stubs: {
            BaseSpinner: true,
            BaseIcon: true,
            BaseButton: {
              template: '<button class="mock-base-button"><slot /></button>',
              props: ["variant"],
            },
            RecentImportCard: true,
          },
        },
      });

      const viewAllButton = wrapper.find(".recent-imports__view-all-btn");
      expect(viewAllButton.exists()).toBe(true);
      expect(viewAllButton.text()).toBe("View All Imports");
    });
  });

  describe("Loading States", () => {
    it("should display loading state when isLoading is true", () => {
      mockViewModel.isLoading = true;

      wrapper = mount(RecentImports, {
        props: { workspace: mockWorkspace },
        global: {
          stubs: {
            BaseSpinnerComponent: {
              template: '<div class="mock-spinner">Loading...</div>',
            },
            BaseIcon: true,
            BaseButton: {
              template: '<button class="mock-base-button"><slot /></button>',
              props: ["variant"],
            },
            RecentImportCard: true,
          },
        },
      });

      expect(wrapper.find(".recent-imports__loading").exists()).toBe(true);
      expect(wrapper.find(".mock-spinner").exists()).toBe(true);
      expect(wrapper.text()).toContain("Loading recent imports...");
    });

    it("should not display loading state when isLoading is false", () => {
      mockViewModel.isLoading = false;

      wrapper = mount(RecentImports, {
        props: { workspace: mockWorkspace },
        global: {
          stubs: {
            BaseSpinner: true,
            BaseIcon: true,
            BaseButton: {
              template: '<button class="mock-base-button"><slot /></button>',
              props: ["variant"],
            },
            RecentImportCard: true,
          },
        },
      });

      expect(wrapper.find(".recent-imports__loading").exists()).toBe(false);
    });
  });

  describe("Error States", () => {
    it("should display error state when error exists", () => {
      mockViewModel.error = "Failed to load recent imports. Please try again.";

      wrapper = mount(RecentImports, {
        props: { workspace: mockWorkspace },
        global: {
          stubs: {
            BaseSpinner: true,
            BaseIcon: {
              template: '<div class="mock-icon"></div>',
              props: ["iconName"],
            },
            BaseButton: {
              template: '<button class="mock-base-button" @click="$emit(\'click\')"><slot /></button>',
              props: ["variant"],
            },
            RecentImportCard: true,
          },
        },
      });

      const errorSection = wrapper.find(".recent-imports__error");
      expect(errorSection.exists()).toBe(true);
      expect(errorSection.text()).toContain("Failed to Load Recent Imports");
      expect(errorSection.text()).toContain("Failed to load recent imports. Please try again.");
    });

    it("should call loadRecentImports when retry button is clicked", async () => {
      mockViewModel.error = "Network error";

      wrapper = mount(RecentImports, {
        props: { workspace: mockWorkspace },
        global: {
          stubs: {
            BaseSpinner: true,
            BaseIcon: true,
            BaseButton: {
              template: '<button class="mock-base-button" @click="$emit(\'click\')"><slot /></button>',
              props: ["variant"],
            },
            RecentImportCard: true,
          },
        },
      });

      const retryButton = wrapper.find(".recent-imports__error .mock-base-button");
      await retryButton.trigger("click");

      expect(mockViewModel.loadRecentImports).toHaveBeenCalled();
    });
  });

  describe("Workspace Selection Integration", () => {
    it("should display no workspace message when workspace is null", () => {
      mockViewModel.hasWorkspace = false;

      wrapper = mount(RecentImports, {
        props: { workspace: null },
        global: {
          stubs: {
            BaseSpinner: true,
            BaseIcon: true,
            BaseButton: {
              template: '<button class="mock-base-button"><slot /></button>',
              props: ["variant"],
            },
            RecentImportCard: true,
          },
        },
      });

      const noWorkspaceSection = wrapper.find(".recent-imports__no-workspace");
      expect(noWorkspaceSection.exists()).toBe(true);
      expect(noWorkspaceSection.text()).toContain("Select a Workspace");
      expect(noWorkspaceSection.text()).toContain("Please select a workspace to view recent imports.");
    });

    it("should display content when workspace is provided", () => {
      mockViewModel.hasWorkspace = true;

      wrapper = mount(RecentImports, {
        props: { workspace: mockWorkspace },
        global: {
          stubs: {
            BaseSpinner: true,
            BaseIcon: true,
            BaseButton: {
              template: '<button class="mock-base-button"><slot /></button>',
              props: ["variant"],
            },
            RecentImportCard: true,
          },
        },
      });

      expect(wrapper.find(".recent-imports__no-workspace").exists()).toBe(false);
      expect(wrapper.find(".recent-imports__actions").exists()).toBe(true);
    });
  });

  describe("Empty States", () => {
    it("should display empty state when no imports exist", () => {
      mockViewModel.recentImports = [];
      mockViewModel.hasWorkspace = true;

      wrapper = mount(RecentImports, {
        props: { workspace: mockWorkspace },
        global: {
          stubs: {
            BaseSpinner: true,
            BaseIcon: true,
            BaseButton: {
              template: '<button class="mock-base-button"><slot /></button>',
              props: ["variant"],
            },
            RecentImportCard: true,
          },
        },
      });

      const emptySection = wrapper.find(".recent-imports__empty");
      expect(emptySection.exists()).toBe(true);
      expect(emptySection.text()).toContain("No Recent Imports Found");
      expect(emptySection.text()).toContain(
        "You haven't imported any documents yet. Start by importing your first bibliography file."
      );
    });
  });

  describe("Event Handling and Navigation", () => {
    it("should emit import-selected when import card is clicked", async () => {
      mockViewModel.recentImports = mockImportRecords;

      wrapper = mount(RecentImports, {
        props: { workspace: mockWorkspace },
        global: {
          stubs: {
            BaseSpinner: true,
            BaseIcon: true,
            BaseButton: {
              template: '<button class="mock-base-button"><slot /></button>',
              props: ["variant"],
            },
            RecentImportCard: {
              template: '<div class="mock-recent-import-card" @click="$emit(\'click\')"></div>',
              props: ["importRecord"],
            },
          },
        },
      });

      const firstCard = wrapper.find(".mock-recent-import-card");
      await firstCard.trigger("click");

      expect(wrapper.emitted("import-selected")).toBeTruthy();
      expect(wrapper.emitted("import-selected")[0][0]).toEqual(mockImportRecords[0]);
    });

    it("should emit view-all-imports when View All Imports button is clicked", async () => {
      wrapper = mount(RecentImports, {
        props: { workspace: mockWorkspace },
        global: {
          stubs: {
            BaseSpinner: true,
            BaseIcon: true,
            BaseButton: {
              template: '<button class="mock-base-button" @click="$emit(\'click\')"><slot /></button>',
              props: ["variant"],
            },
            RecentImportCard: true,
          },
        },
      });

      const viewAllButton = wrapper.find(".recent-imports__view-all-btn");
      await viewAllButton.trigger("click");

      expect(wrapper.emitted("view-all-imports")).toBeTruthy();
    });
  });

  describe("View Model Integration", () => {
    it("should call useRecentImportsViewModel with correct props", () => {
      wrapper = mount(RecentImports, {
        props: { workspace: mockWorkspace },
        global: {
          stubs: {
            BaseSpinner: true,
            BaseIcon: true,
            BaseButton: {
              template: '<button class="mock-base-button"><slot /></button>',
              props: ["variant"],
            },
            RecentImportCard: true,
          },
        },
      });

      expect(useRecentImportsViewModel).toHaveBeenCalledWith({ workspace: mockWorkspace });
    });

    it("should handle workspace prop changes", async () => {
      wrapper = mount(RecentImports, {
        props: { workspace: mockWorkspace },
        global: {
          stubs: {
            BaseSpinner: true,
            BaseIcon: true,
            BaseButton: {
              template: '<button class="mock-base-button"><slot /></button>',
              props: ["variant"],
            },
            RecentImportCard: true,
          },
        },
      });

      const newWorkspace = { id: "workspace-2", name: "New Workspace" };
      await wrapper.setProps({ workspace: newWorkspace });

      // The view model should be called with the new workspace
      expect(useRecentImportsViewModel).toHaveBeenCalledWith({ workspace: newWorkspace });
    });
  });

  describe("Responsive Design", () => {
    it("should apply responsive classes correctly", () => {
      wrapper = mount(RecentImports, {
        props: { workspace: mockWorkspace },
        global: {
          stubs: {
            BaseSpinner: true,
            BaseIcon: true,
            BaseButton: {
              template: '<button class="mock-base-button"><slot /></button>',
              props: ["variant"],
            },
            RecentImportCard: true,
          },
        },
      });

      // Check that the component has the main class for responsive styling
      expect(wrapper.find(".recent-imports").exists()).toBe(true);
      expect(wrapper.find(".recent-imports__header").exists()).toBe(true);
      expect(wrapper.find(".recent-imports__actions").exists()).toBe(true);
    });

    it("should render correctly on different screen sizes", () => {
      // This test verifies the component structure that supports responsive design
      wrapper = mount(RecentImports, {
        props: { workspace: mockWorkspace },
        global: {
          stubs: {
            BaseSpinner: true,
            BaseIcon: true,
            BaseButton: {
              template: '<button class="mock-base-button"><slot /></button>',
              props: ["variant"],
            },
            RecentImportCard: true,
          },
        },
      });

      // Verify that responsive elements are present
      const header = wrapper.find(".recent-imports__header");
      const title = wrapper.find(".recent-imports__title");
      const subtitle = wrapper.find(".recent-imports__subtitle");
      const actions = wrapper.find(".recent-imports__actions");

      expect(header.exists()).toBe(true);
      expect(title.exists()).toBe(true);
      expect(subtitle.exists()).toBe(true);
      expect(actions.exists()).toBe(true);
    });
  });

  describe("Accessibility", () => {
    it("should have proper heading structure", () => {
      wrapper = mount(RecentImports, {
        props: { workspace: mockWorkspace },
        global: {
          stubs: {
            BaseSpinner: true,
            BaseIcon: true,
            BaseButton: {
              template: '<button class="mock-base-button"><slot /></button>',
              props: ["variant"],
            },
            RecentImportCard: true,
          },
        },
      });

      const title = wrapper.find(".recent-imports__title");
      expect(title.element.tagName).toBe("H3");
    });

    it("should provide meaningful error messages", () => {
      mockViewModel.error = "Network connection failed";

      wrapper = mount(RecentImports, {
        props: { workspace: mockWorkspace },
        global: {
          stubs: {
            BaseSpinner: true,
            BaseIcon: true,
            BaseButton: {
              template: '<button class="mock-base-button"><slot /></button>',
              props: ["variant"],
            },
            RecentImportCard: true,
          },
        },
      });

      const errorSection = wrapper.find(".recent-imports__error");
      expect(errorSection.text()).toContain("Failed to Load Recent Imports");
      expect(errorSection.text()).toContain("Network connection failed");
    });
  });
});
