import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import DatasetSettingsModal from "./DatasetSettingsModal.vue";
import { useDatasetSettingsModal } from "@/v1/store/datasetSettingsModal";

// Mock the dependencies
jest.mock("@/v1/infrastructure/services/useRoutes", () => ({
  useRoutes: () => ({
    goToFeedbackTaskAnnotationPage: jest.fn(),
  }),
}));

jest.mock("./useDatasetSettingModalViewModel", () => ({
  useDatasetSettingModalViewModel: () => ({
    isLoadingDataset: false,
    breadcrumbs: [],
    tabs: [],
    isAdminOrOwnerRole: true,
    datasetSetting: {},
    goToOutside: jest.fn((callback) => callback()),
    goToDataset: jest.fn(),
    onTabChanged: jest.fn(),
    onTabLoaded: jest.fn(),
  }),
}));

describe("DatasetSettingsModal", () => {
  let modalStore;

  beforeEach(() => {
    setActivePinia(createPinia());
    modalStore = useDatasetSettingsModal();
  });

  it("should render when modal is visible", async () => {
    modalStore.openModal("test-dataset-id");
    
    const wrapper = mount(DatasetSettingsModal, {
      stubs: {
        BaseModal: {
          template: '<div class="mock-base-modal"><slot /></div>',
          props: ["modalVisible", "modalClass", "modalTitle"],
        },
        BaseLoading: '<div class="mock-loading">Loading...</div>',
        BaseButton: {
          template: '<button class="mock-button"><slot /></button>',
          props: ["class"],
        },
        BaseTabsAndContent: {
          template: '<div class="mock-tabs"><slot /></div>',
          props: ["tabs", "tabSize", "class"],
        },
        SettingsInfoReadOnly: '<div class="mock-settings-readonly"></div>',
      },
    });
    
    expect(wrapper.find(".mock-base-modal").exists()).toBe(true);
  });

  it("should not render when modal is not visible", async () => {
    modalStore.closeModal();
    
    const wrapper = mount(DatasetSettingsModal, {
      stubs: {
        BaseModal: {
          template: '<div class="mock-base-modal"><slot /></div>',
          props: ["modalVisible", "modalClass", "modalTitle"],
        },
        BaseLoading: '<div class="mock-loading">Loading...</div>',
        BaseButton: {
          template: '<button class="mock-button"><slot /></button>',
          props: ["class"],
        },
        BaseTabsAndContent: {
          template: '<div class="mock-tabs"><slot /></div>',
          props: ["tabs", "tabSize", "class"],
        },
        SettingsInfoReadOnly: '<div class="mock-settings-readonly"></div>',
      },
    });
    
    expect(wrapper.find(".mock-base-modal").exists()).toBe(false);
  });

  it("should call closeModal when closeModal method is called", () => {
    modalStore.openModal("test-dataset-id");
    
    const wrapper = mount(DatasetSettingsModal, {
      stubs: {
        BaseModal: {
          template: '<div class="mock-base-modal"><slot /></div>',
          props: ["modalVisible", "modalClass", "modalTitle"],
        },
        BaseLoading: '<div class="mock-loading">Loading...</div>',
        BaseButton: {
          template: '<button class="mock-button"><slot /></button>',
          props: ["class"],
        },
        BaseTabsAndContent: {
          template: '<div class="mock-tabs"><slot /></div>',
          props: ["tabs", "tabSize", "class"],
        },
        SettingsInfoReadOnly: '<div class="mock-settings-readonly"></div>',
      },
    });
    
    wrapper.vm.closeModal();
    
    expect(modalStore.isVisible).toBe(false);
  });

  it("should store dataset ID when modal is opened", () => {
    const testDatasetId = "test-dataset-123";
    
    modalStore.openModal(testDatasetId);
    
    expect(modalStore.datasetId).toBe(testDatasetId);
  });
});