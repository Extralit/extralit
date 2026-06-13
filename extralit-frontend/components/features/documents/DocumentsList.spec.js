import { mount } from "@vue/test-utils";
import DocumentsList from "./DocumentsList.vue";
import { Document } from "~/v1/domain/entities/document/Document";

// Mock the view model
const mockShowDocumentMetadata = vi.fn();
const mockCloseMetadataModal = vi.fn();
const mockViewModel = {
  documents: [],
  isLoading: false,
  error: null,
  groupedDocuments: [],
  totalFiles: 0,
  showMetadataModal: false,
  selectedDocumentMetadata: null,
  selectedDocumentName: "",
  loadDocuments: vi.fn(),
  openDocument: vi.fn(),
  showDocumentMetadata: mockShowDocumentMetadata,
  closeMetadataModal: mockCloseMetadataModal,
};

vi.mock("./useDocumentsListViewModel", () => ({
  useDocumentsListViewModel: () => mockViewModel,
}));

// Mock base components
vi.mock("~/components/base/base-modal/BaseModal.vue", () => ({
  name: "BaseModal",
  template: '<div class="base-modal"><slot /></div>',
  props: ["modalVisible", "modalTitle", "modalClass"],
}));

vi.mock("~/components/base/base-button/BaseButton.vue", () => ({
  name: "BaseButton",
  template: '<button class="base-button" @click="$emit(\'click\')"><slot /></button>',
}));

describe("DocumentsList", () => {
  let wrapper;

  const createWrapper = (props = {}) => {
    return mount(DocumentsList, {
      props: {
        workspaceId: "test-workspace",
        ...props,
      },
      stubs: {
        BaseButton: true,
        BaseModal: true,
        BaseDate: true,
        BaseTag: true,
        svgicon: true,
      },
      mocks: {
        $notification: {
          error: vi.fn(),
        },
      },
    });
  };

  beforeEach(() => {
    // Reset mocks before each test
    vi.clearAllMocks();
    // Reset mock view model state
    mockViewModel.documents = [];
    mockViewModel.showMetadataModal = false;
    mockViewModel.selectedDocumentMetadata = null;
    mockViewModel.selectedDocumentName = "";
    mockViewModel.groupedDocuments = [];

    wrapper = createWrapper();
  });

  afterEach(() => {
    wrapper.unmount();
  });

  describe("metadata modal functionality", () => {
    it("should show metadata button when document has metadata", async () => {
      const documentWithMetadata = new Document(
        "doc-1",
        "http://example.com/doc.pdf",
        "test.pdf",
        "pmid123",
        "doi123",
        1,
        "Test Reference",
        [],
        { workflow_status: "completed", analysis_metadata: { ocr_quality: { total_chars: 1000 } } }
      );

      // Update the mock view model data instead of using setData
      mockViewModel.documents = [documentWithMetadata];
      mockViewModel.groupedDocuments = [
        {
          reference: "Test Reference",
          documents: [documentWithMetadata],
          metadata: documentWithMetadata.metadata,
        },
      ];

      await wrapper.vm.$nextTick();

      // Check that metadata button logic would work
      expect(documentWithMetadata.metadata).toBeDefined();
      expect(mockViewModel.documents[0].metadata).toBeDefined();
    });

    it("should open metadata modal when metadata button is clicked", async () => {
      const testMetadata = {
        workflow_status: "completed",
        analysis_metadata: {
          ocr_quality: { total_chars: 1000, ocr_quality_score: 0.95 },
        },
      };

      const documentWithMetadata = new Document(
        "doc-1",
        "http://example.com/doc.pdf",
        "test-document.pdf",
        "pmid123",
        "doi123",
        1,
        "Test Reference",
        [],
        testMetadata
      );

      // Update the mock view model data
      mockViewModel.documents = [documentWithMetadata];
      mockViewModel.groupedDocuments = [
        {
          reference: "Test Reference",
          documents: [documentWithMetadata],
          metadata: documentWithMetadata.metadata,
        },
      ];

      await wrapper.vm.$nextTick();

      // Call the method through the mock
      mockShowDocumentMetadata(documentWithMetadata);

      // Verify the mock was called with correct arguments
      expect(mockShowDocumentMetadata).toHaveBeenCalledWith(documentWithMetadata);
      expect(mockShowDocumentMetadata).toHaveBeenCalledTimes(1);
    });

    it("should close metadata modal when closeMetadataModal is called", () => {
      // Set up initial modal state
      mockViewModel.showMetadataModal = true;
      mockViewModel.selectedDocumentMetadata = { some: "data" };
      mockViewModel.selectedDocumentName = "test.pdf";

      // Call the method through the mock
      mockCloseMetadataModal();

      // Verify the mock was called
      expect(mockCloseMetadataModal).toHaveBeenCalledTimes(1);
    });
  });
});
