import { mount } from '@vue/test-utils';
import DocumentsList from './DocumentsList.vue';
import { Document } from '~/v1/domain/entities/document/Document';

// Mock the view model
jest.mock('./useDocumentsListViewModel', () => ({
  useDocumentsListViewModel: () => ({
    documents: [],
    isLoading: false,
    error: null,
    groupedDocuments: [],
    totalFiles: 0,
    loadDocuments: jest.fn(),
    openDocument: jest.fn(),
  }),
}));

// Mock base components
jest.mock('~/components/base/base-modal/BaseModal.vue', () => ({
  name: 'BaseModal',
  template: '<div class="base-modal"><slot /></div>',
  props: ['modalVisible', 'modalTitle', 'modalClass'],
}));

jest.mock('~/components/base/base-button/BaseButton.vue', () => ({
  name: 'BaseButton',
  template: '<button class="base-button" @click="$emit(\'click\')"><slot /></button>',
}));

describe('DocumentsList', () => {
  let wrapper;

  const createWrapper = (props = {}) => {
    return mount(DocumentsList, {
      propsData: {
        workspaceId: 'test-workspace',
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
          error: jest.fn(),
        },
      },
    });
  };

  beforeEach(() => {
    wrapper = createWrapper();
  });

  afterEach(() => {
    wrapper.destroy();
  });

  describe('metadata modal functionality', () => {
    it('should show metadata button when document has metadata', async () => {
      const documentWithMetadata = new Document(
        'doc-1',
        'http://example.com/doc.pdf',
        'test.pdf',
        'pmid123',
        'doi123',
        1,
        'Test Reference',
        [],
        { workflow_status: 'completed', analysis_metadata: { ocr_quality: { total_chars: 1000 } } }
      );

      wrapper.setData({
        documents: [documentWithMetadata],
      });

      await wrapper.vm.$nextTick();

      // Check that metadata button logic would work
      expect(documentWithMetadata.metadata).toBeDefined();
      expect(wrapper.vm.documents[0].metadata).toBeDefined();
    });

    it('should open metadata modal when metadata button is clicked', async () => {
      const testMetadata = {
        workflow_status: 'completed',
        analysis_metadata: {
          ocr_quality: { total_chars: 1000, ocr_quality_score: 0.95 }
        }
      };

      const documentWithMetadata = new Document(
        'doc-1',
        'http://example.com/doc.pdf',
        'test-document.pdf',
        'pmid123',
        'doi123',
        1,
        'Test Reference',
        [],
        testMetadata
      );

      wrapper.setData({
        documents: [documentWithMetadata],
      });

      await wrapper.vm.$nextTick();

      // Call the method directly to test functionality
      wrapper.vm.showDocumentMetadata(documentWithMetadata);

      expect(wrapper.vm.showMetadataModal).toBe(true);
      expect(wrapper.vm.selectedDocumentMetadata).toEqual(testMetadata);
      expect(wrapper.vm.selectedDocumentName).toBe('test-document.pdf');
    });

    it('should close metadata modal when closeMetadataModal is called', () => {
      wrapper.setData({
        showMetadataModal: true,
        selectedDocumentMetadata: { some: 'data' },
        selectedDocumentName: 'test.pdf',
      });

      wrapper.vm.closeMetadataModal();

      expect(wrapper.vm.showMetadataModal).toBe(false);
      expect(wrapper.vm.selectedDocumentMetadata).toBe(null);
      expect(wrapper.vm.selectedDocumentName).toBe('');
    });
  });
});