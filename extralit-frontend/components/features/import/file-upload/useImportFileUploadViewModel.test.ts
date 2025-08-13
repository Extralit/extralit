/**
 * Unit tests for useImportFileUploadViewModel composable
 */
import { createBibStrategy, createPdfStrategy, useImportFileUploadViewModel } from './useImportFileUploadViewModel';

// Mock file parsing service
const mockFileParsingService = {
  isValidFileType: jest.fn(),
  readFileContent: jest.fn(),
  parseBibTeX: jest.fn(),
  parseCSVForPreview: jest.fn(),
  parseCSVWithConfig: jest.fn(),
};

// Mock PDF matching service
const mockPdfMatchingService = {
  matchFiles: jest.fn(),
};

// Mock file objects
const createMockFile = (name: string, type: string, size: number = 1000): File => ({
  name,
  type,
  size,
  lastModified: Date.now(),
  slice: jest.fn(),
  stream: jest.fn(),
  text: jest.fn(),
  arrayBuffer: jest.fn(),
} as unknown as File);

describe('useImportFileUploadViewModel', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('createBibStrategy', () => {
    it('should validate .bib files correctly', async () => {
      mockFileParsingService.isValidFileType.mockReturnValue(true);
      
      const strategy = createBibStrategy({
        fileParsingService: mockFileParsingService,
      });

      const validFile = createMockFile('test.bib', 'text/plain', 1000);
      const result = await strategy.validateFiles([validFile]);

      expect(result.validFiles).toHaveLength(1);
      expect(result.errors).toHaveLength(0);
      expect(mockFileParsingService.isValidFileType).toHaveBeenCalledWith(validFile, ['.bib', '.bibtex', '.csv']);
    });

    it('should reject files that are too large', async () => {
      mockFileParsingService.isValidFileType.mockReturnValue(true);
      
      const strategy = createBibStrategy({
        fileParsingService: mockFileParsingService,
      });

      const largeFile = createMockFile('test.bib', 'text/plain', 100 * 1024 * 1024); // 100MB
      const result = await strategy.validateFiles([largeFile]);

      expect(result.validFiles).toHaveLength(0);
      expect(result.errors).toHaveLength(1);
      expect(result.errors[0]).toContain('too large');
    });

    it('should process BibTeX files directly', async () => {
      const mockTableData = { data: [{ reference: 'test1' }] };
      mockFileParsingService.readFileContent.mockResolvedValue('mock content');
      mockFileParsingService.parseBibTeX.mockResolvedValue(mockTableData);
      
      const strategy = createBibStrategy({
        fileParsingService: mockFileParsingService,
      });

      const bibFile = createMockFile('test.bib', 'text/plain');
      const result = await strategy.processFiles([bibFile]);

      expect(result.fileName).toBe('test.bib');
      expect(result.dataframeData).toBe(mockTableData);
      expect(result.type).toBe('bibliography');
    });

    it('should validate data correctly', () => {
      const strategy = createBibStrategy({
        fileParsingService: mockFileParsingService,
      });

      expect(strategy.isValid({ dataframeData: { data: [{ ref: 'test' }] } })).toBe(true);
      expect(strategy.isValid({ dataframeData: { data: [] } })).toBe(false);
      expect(strategy.isValid({})).toBe(false);
    });
  });

  describe('createPdfStrategy', () => {
    it('should validate PDF files correctly', async () => {
      const strategy = createPdfStrategy({
        pdfMatchingService: mockPdfMatchingService,
      });

      const validPdf = createMockFile('test.pdf', 'application/pdf', 1000);
      const result = await strategy.validateFiles([validPdf]);

      expect(result.validFiles).toHaveLength(1);
      expect(result.errors).toHaveLength(0);
    });

    it('should reject oversized PDF files', async () => {
      const strategy = createPdfStrategy({
        pdfMatchingService: mockPdfMatchingService,
        maxFileSize: 1000, // 1KB limit for testing
      });

      const largePdf = createMockFile('test.pdf', 'application/pdf', 2000);
      const result = await strategy.validateFiles([largePdf]);

      expect(result.validFiles).toHaveLength(0);
      expect(result.errors).toHaveLength(1);
      expect(result.errors[0]).toContain('too large');
    });

    it('should process PDF files with matching', async () => {
      const mockMatchingResult = {
        matchedFiles: [{ file: 'file1', bibEntry: 'entry1' }],
        unmatchedFiles: []
      };
      
      mockPdfMatchingService.matchFiles.mockReturnValue(mockMatchingResult);
      
      const strategy = createPdfStrategy({
        pdfMatchingService: mockPdfMatchingService,
        bibliographyEntries: { data: [{ reference: 'test' }] }
      });

      const pdfFile = createMockFile('test.pdf', 'application/pdf');
      const result = await strategy.processFiles([pdfFile]);

      expect(result.matchedFiles).toBe(mockMatchingResult.matchedFiles);
      expect(result.unmatchedFiles).toBe(mockMatchingResult.unmatchedFiles);
      expect(result.type).toBe('pdf');
    });

    it('should validate data correctly', () => {
      const strategy = createPdfStrategy({
        pdfMatchingService: mockPdfMatchingService,
      });

      expect(strategy.isValid({ matchedFiles: [{ file: 'test' }] })).toBe(true);
      expect(strategy.isValid({ matchedFiles: [] })).toBe(false);
      expect(strategy.isValid({})).toBe(false);
    });
  });

  describe('useImportFileUploadViewModel basic functionality', () => {
    it('should create view model with correct initial state', () => {
      const mockStrategy = createBibStrategy({
        fileParsingService: mockFileParsingService,
      });

      const viewModel = useImportFileUploadViewModel(mockStrategy);

      expect(viewModel.state.isDragging).toBe(false);
      expect(viewModel.state.uploaded).toBe(false);
      expect(viewModel.state.hasError).toBe(false);
      expect(viewModel.state.processing).toBe(false);
      expect(viewModel.isValid()).toBe(false);
    });

    it('should reset state correctly', () => {
      const mockStrategy = createBibStrategy({
        fileParsingService: mockFileParsingService,
      });

      const onUpdate = jest.fn();
      const viewModel = useImportFileUploadViewModel(mockStrategy, { onUpdate });

      // Set some state
      viewModel.state.uploaded = true;
      viewModel.state.hasError = true;
      
      viewModel.reset();

      expect(viewModel.state.uploaded).toBe(false);
      expect(viewModel.state.hasError).toBe(false);
      expect(onUpdate).toHaveBeenCalledWith(null);
    });

    it('should initialize with existing data', () => {
      const mockStrategy = createBibStrategy({
        fileParsingService: mockFileParsingService,
      });

      const viewModel = useImportFileUploadViewModel(mockStrategy);
      const initialData = { dataframeData: { data: [{ ref: 'test' }] } };

      viewModel.initialize(initialData);

      expect(viewModel.state.data).toBe(initialData);
      expect(viewModel.state.uploaded).toBe(true);
    });
  });
});