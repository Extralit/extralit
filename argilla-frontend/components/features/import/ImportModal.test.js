import { mount } from '@vue/test-utils'
import ImportModal from './ImportModal.vue'

describe('ImportModal', () => {
  let wrapper

  beforeEach(() => {
    wrapper = mount(ImportModal, {
      propsData: {
        isVisible: true
      },
      stubs: {
        'base-modal': true,
        'base-button': true,
        'base-spinner': true,
        'import-bib-upload': true,
        'import-pdf-upload': true,
        'import-analysis-table': true,
        'import-batch-progress': true,
        'import-summary': true,
        'svgicon': true
      }
    })
  })

  afterEach(() => {
    wrapper.destroy()
  })

  describe('Modal State Management', () => {
    it('should initialize with correct default state', () => {
      expect(wrapper.vm.currentStep).toBe(1)
      expect(wrapper.vm.totalSteps).toBe(5)
      expect(wrapper.vm.isProcessing).toBe(false)
      expect(wrapper.vm.isAnalyzing).toBe(false)
      expect(wrapper.vm.isUploading).toBe(false)
      expect(wrapper.vm.hasError).toBe(false)
    })

    it('should reset modal state when isVisible changes to true', async () => {
      wrapper.vm.currentStep = 3
      wrapper.vm.hasError = true
      wrapper.vm.errorMessage = 'Test error'

      await wrapper.setProps({ isVisible: false })
      await wrapper.setProps({ isVisible: true })

      expect(wrapper.vm.currentStep).toBe(1)
      expect(wrapper.vm.hasError).toBe(false)
      expect(wrapper.vm.errorMessage).toBe('')
    })
  })

  describe('Step Navigation', () => {
    it('should calculate progress percentage correctly', () => {
      wrapper.vm.currentStep = 1
      expect(wrapper.vm.progressPercentage).toBe(20)

      wrapper.vm.currentStep = 3
      expect(wrapper.vm.progressPercentage).toBe(60)

      wrapper.vm.currentStep = 5
      expect(wrapper.vm.progressPercentage).toBe(100)
    })

    it('should determine step progression conditions correctly', () => {
      // Step 1: Need parsed entries
      expect(wrapper.vm.canProceedFromStep1).toBe(false)

      wrapper.vm.bibData.parsedEntries = [{ reference: 'test' }]
      expect(wrapper.vm.canProceedFromStep1).toBe(true)

      // Step 2: Need matched files
      expect(wrapper.vm.canProceedFromStep2).toBe(false)

      wrapper.vm.pdfData.matchedFiles = [{ filename: 'test.pdf' }]
      expect(wrapper.vm.canProceedFromStep2).toBe(true)

      // Step 3: Need analysis data
      expect(wrapper.vm.canProceedFromStep3).toBe(false)

      wrapper.vm.analysisData.documents = { 'test': {} }
      expect(wrapper.vm.canProceedFromStep3).toBe(true)
    })

    it('should navigate to next step when conditions are met', () => {
      wrapper.vm.bibData.parsedEntries = [{ reference: 'test' }]

      wrapper.vm.goToNextStep()
      expect(wrapper.vm.currentStep).toBe(2)
    })

    it('should navigate to previous step correctly', () => {
      wrapper.vm.currentStep = 3

      wrapper.vm.goToPreviousStep()
      expect(wrapper.vm.currentStep).toBe(2)
    })

    it('should not allow navigation beyond valid range', () => {
      wrapper.vm.currentStep = 1
      wrapper.vm.goToPreviousStep()
      expect(wrapper.vm.currentStep).toBe(1)

      wrapper.vm.currentStep = 4
      wrapper.vm.goToPreviousStep()
      expect(wrapper.vm.currentStep).toBe(4) // Can't go back from step 4 (upload in progress)
    })
  })

  describe('Step Data Handlers', () => {
    it('should handle BibTeX file parsed event', () => {
      const mockData = {
        fileName: 'test.bib',
        parsedEntries: [{ reference: 'test' }],
        dataframeData: { schema: {}, data: [] },
        rawContent: 'mock content'
      }

      wrapper.vm.handleBibFileParsed(mockData)

      expect(wrapper.vm.bibData).toEqual(mockData)
      expect(wrapper.vm.hasError).toBe(false)
    })

    it('should handle PDF files matched event', () => {
      const mockData = {
        matchedFiles: [{ filename: 'test.pdf' }],
        unmatchedFiles: [],
        totalFiles: 1
      }

      wrapper.vm.handlePdfFilesMatched(mockData)

      expect(wrapper.vm.pdfData).toEqual(mockData)
      expect(wrapper.vm.hasError).toBe(false)
    })

    it('should handle analysis confirmed event', () => {
      const mockDocuments = { 'test': { action: 'add' } }

      wrapper.vm.handleAnalysisConfirmed(mockDocuments)

      expect(wrapper.vm.uploadData.confirmedDocuments).toEqual(mockDocuments)
      expect(wrapper.vm.hasError).toBe(false)
    })

    it('should handle upload completed event', () => {
      const mockSummary = {
        totalProcessed: 10,
        successfullyAdded: 8,
        updated: 1,
        skipped: 1,
        failed: 0,
        errors: [],
        importId: 'test-import-123'
      }

      wrapper.vm.handleUploadCompleted(mockSummary)

      expect(wrapper.vm.summaryData).toEqual(mockSummary)
      expect(wrapper.vm.isUploading).toBe(false)
      expect(wrapper.vm.currentStep).toBe(5)
      expect(wrapper.vm.hasError).toBe(false)
    })
  })

  describe('Error Handling', () => {
    it('should show error with retry option', () => {
      wrapper.vm.showError('Test error message', true)

      expect(wrapper.vm.hasError).toBe(true)
      expect(wrapper.vm.errorMessage).toBe('Test error message')
      expect(wrapper.vm.canRetryError).toBe(true)
    })

    it('should clear error state', () => {
      wrapper.vm.hasError = true
      wrapper.vm.errorMessage = 'Test error'
      wrapper.vm.canRetryError = true

      wrapper.vm.clearError()

      expect(wrapper.vm.hasError).toBe(false)
      expect(wrapper.vm.errorMessage).toBe('')
      expect(wrapper.vm.canRetryError).toBe(false)
    })

    it('should handle validation errors', () => {
      const mockError = { message: 'Validation failed' }

      wrapper.vm.handleValidationError(mockError)

      expect(wrapper.vm.hasError).toBe(true)
      expect(wrapper.vm.errorMessage).toBe('Validation failed')
      expect(wrapper.vm.canRetryError).toBe(true)
    })
  })

  describe('Modal Lifecycle', () => {
    it('should emit close event when handleClose is called', () => {
      wrapper.vm.handleClose()

      expect(wrapper.emitted('close')).toBeTruthy()
    })

    it('should emit navigation events', () => {
      wrapper.vm.handleReturnToLibrary()
      expect(wrapper.emitted('navigate-to-library')).toBeTruthy()

      wrapper.vm.handleViewImportHistory()
      expect(wrapper.emitted('navigate-to-import-history')).toBeTruthy()
    })

    it('should reset all data when resetModal is called', () => {
      // Set some state
      wrapper.vm.currentStep = 3
      wrapper.vm.hasError = true
      wrapper.vm.bibData.parsedEntries = [{ test: 'data' }]

      wrapper.vm.resetModal()

      expect(wrapper.vm.currentStep).toBe(1)
      expect(wrapper.vm.hasError).toBe(false)
      expect(wrapper.vm.bibData.parsedEntries).toEqual([])
    })
  })

  describe('Step Definitions', () => {
    it('should have correct step definitions', () => {
      expect(wrapper.vm.steps).toHaveLength(5)
      expect(wrapper.vm.steps[0].id).toBe('bib-upload')
      expect(wrapper.vm.steps[1].id).toBe('pdf-upload')
      expect(wrapper.vm.steps[2].id).toBe('analysis')
      expect(wrapper.vm.steps[3].id).toBe('progress')
      expect(wrapper.vm.steps[4].id).toBe('summary')
    })
  })

  describe('Async Operations', () => {
    it('should handle import analysis', async () => {
      // Set up bibData with parsed entries first
      wrapper.vm.bibData.parsedEntries = [{ reference: 'test' }]

      // Ensure isAnalyzing is false before starting
      wrapper.vm.isAnalyzing = false

      await wrapper.vm.performImportAnalysis()

      // Just check that the method completes without error
      expect(wrapper.vm.isAnalyzing).toBe(false)
      expect(wrapper.vm.analysisData).toBeDefined()
    })

    it('should handle analysis errors', async () => {
      jest.spyOn(wrapper.vm, 'callImportAnalysisAPI').mockRejectedValue(new Error('API Error'))

      await wrapper.vm.performImportAnalysis()

      expect(wrapper.vm.isAnalyzing).toBe(false)
      expect(wrapper.vm.hasError).toBe(true)
      expect(wrapper.vm.errorMessage).toContain('Analysis failed')
    })
  })
})