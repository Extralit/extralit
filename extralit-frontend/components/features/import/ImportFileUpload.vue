<template>
  <div class="import-file-upload">
    <div class="import-file-upload__header">
      <h1 class="import-file-upload__title">Upload Bibliography and PDF Files</h1>
      <p class="import-file-upload__description">Upload your bibliography file and PDF folder to import your library</p>
    </div>

    <div class="import-file-upload__content">
      <div class="import-file-upload__main">
        <!-- Bibliography Upload Section -->
        <div class="import-file-upload__section">
          <div class="import-file-upload__section-header">
            <h3 class="import-file-upload__section-title">Step 1: Upload Your Bibliography File</h3>
            <p class="import-file-upload__section-description">
              Import your reference list to begin.<br />
              We support .bib files exported from reference managers like Zotero, EndNote, or Mendeley, and .csv files with tabular data.
            </p>
          </div>

          <div class="import-file-upload__dropzone" :class="{
            'import-file-upload__dropzone--dragover': bibDragOver,
            'import-file-upload__dropzone--error': bibHasError,
            'import-file-upload__dropzone--success': bibUploaded,
          }" @drop="handleBibDrop" @dragover="handleBibDragOver" @dragleave="handleBibDragLeave"
            @click="triggerBibFileInput">
            <input ref="bibFileInput" type="file" accept=".bib,.bibtex,.csv" style="display: none"
              @change="handleBibFileSelect" />

            <div class="import-file-upload__dropzone-content">
              <BaseIcon :icon-name="getBibDropzoneIcon" class="import-file-upload__dropzone-icon" />
              <p class="import-file-upload__dropzone-text">
                {{ getBibDropzoneText }}
              </p>
              <p class="import-file-upload__dropzone-subtext">Supported formats: .bib, .bibtex, .csv</p>
            </div>
          </div>

          <!-- Bibliography Success Display -->
          <div v-if="bibUploaded && !bibHasError" class="import-file-upload__upload-success">
            <BaseIcon icon-name="check" class="import-file-upload__upload-success-icon" />
            <span class="import-file-upload__upload-success-text">
              Successfully uploaded {{ bibData.fileName }} ({{ bibData.parsedEntries.length }} entries found)
            </span>
          </div>

          <!-- Bibliography Error Display -->
          <div v-if="bibHasError" class="import-file-upload__error">
            <BaseIcon icon-name="danger" class="import-file-upload__error-icon" />
            <div class="import-file-upload__error-content">
              <h4>Bibliography Parsing Error</h4>
              <p>{{ bibErrorMessage }}</p>
            </div>
          </div>

          <!-- CSV Column Selection -->
          <div v-if="showCsvColumnSelection" class="import-file-upload__csv-selection">
            <div class="import-file-upload__csv-selection-header">
              <h4 class="import-file-upload__csv-selection-title">Configure CSV Import</h4>
              <p class="import-file-upload__csv-selection-description">
                Select the columns that contain reference identifiers and file paths for PDF matching.
              </p>
            </div>

            <div class="import-file-upload__csv-columns">
              <div class="import-file-upload__csv-column-group">
                <label class="import-file-upload__csv-column-label">
                  Reference Column (Required)
                  <select v-model="csvConfig.referenceColumn" class="import-file-upload__csv-column-select">
                    <option value="">Select column...</option>
                    <option v-for="column in csvColumns" :key="column" :value="column">
                      {{ column }}
                    </option>
                  </select>
                </label>
                <p class="import-file-upload__csv-column-help">
                  Column containing unique identifiers for each reference (e.g., citation key, ID)
                </p>
              </div>

              <div class="import-file-upload__csv-column-group">
                <label class="import-file-upload__csv-column-label">
                  Files Column (Optional)
                  <select v-model="csvConfig.filesColumn" class="import-file-upload__csv-column-select">
                    <option value="">Select column...</option>
                    <option v-for="column in csvColumns" :key="column" :value="column">
                      {{ column }}
                    </option>
                  </select>
                </label>
                <p class="import-file-upload__csv-column-help">
                  Column containing file paths or names for PDF matching (leave empty if not available)
                </p>
              </div>
            </div>

            <div class="import-file-upload__csv-preview">
              <h5>Data Preview (first 3 rows):</h5>
              <div class="import-file-upload__csv-preview-table">
                <table class="import-file-upload__table">
                  <thead>
                    <tr>
                      <th v-for="column in csvColumns" :key="column" :class="{
                        'import-file-upload__csv-preview-header--selected':
                          column === csvConfig.referenceColumn || column === csvConfig.filesColumn
                      }">
                        {{ column }}
                        <span v-if="column === csvConfig.referenceColumn" class="import-file-upload__csv-preview-badge">REF</span>
                        <span v-if="column === csvConfig.filesColumn" class="import-file-upload__csv-preview-badge">FILES</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, index) in csvPreviewData" :key="index">
                      <td v-for="column in csvColumns" :key="column" :class="{
                        'import-file-upload__csv-preview-cell--selected':
                          column === csvConfig.referenceColumn || column === csvConfig.filesColumn
                      }">
                        {{ row[column] || '' }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div class="import-file-upload__csv-actions">
              <BaseButton
                variant="primary"
                :disabled="!csvConfig.referenceColumn"
                @click="processCsvWithConfig"
              >
                Process CSV Data
              </BaseButton>
              <BaseButton variant="secondary" @click="cancelCsvSelection">
                Cancel
              </BaseButton>
            </div>
          </div>
        </div>

        <!-- PDF Upload Section -->
        <div class="import-file-upload__section">
          <div class="import-file-upload__section-header">
            <h3 class="import-file-upload__section-title">Step 2: Upload Full-Text PDFs</h3>
            <p class="import-file-upload__section-description">
              Upload the PDF files that correspond to the references in your .bib file.<br />
              Extralit will match them automatically for extraction.
            </p>
          </div>

          <div class="import-file-upload__dropzone" :class="{
            'import-file-upload__dropzone--dragover': pdfDragOver,
            'import-file-upload__dropzone--error': pdfHasError,
            'import-file-upload__dropzone--success': pdfUploaded,
          }" @drop="handlePdfDrop" @dragover="handlePdfDragOver" @dragleave="handlePdfDragLeave"
            @click="triggerPdfFolderInput">
            <input ref="pdfFolderInput" type="file" accept=".pdf" multiple webkitdirectory style="display: none"
              @change="handlePdfFolderSelect" />

            <div class="import-file-upload__dropzone-content">
              <BaseIcon :icon-name="getPdfDropzoneIcon" class="import-file-upload__dropzone-icon" />
              <p class="import-file-upload__dropzone-text">
                {{ getPdfDropzoneText }}
              </p>
              <p class="import-file-upload__dropzone-subtext">Upload a folder containing your PDF files.<br /></p>
            </div>
          </div>

          <!-- PDF Processing Progress -->
          <div v-if="pdfProcessing" class="import-file-upload__progress">
            <div class="import-file-upload__progress-header">
              <h4>Processing PDF Files...</h4>
              <span>{{ pdfProcessedFiles }}/{{ pdfTotalFiles }} files</span>
            </div>
            <div class="import-file-upload__progress-bar">
              <div class="import-file-upload__progress-fill" :style="{ width: `${pdfProgressPercentage}%` }"></div>
            </div>
          </div>

          <!-- PDF Success Display -->
          <div v-if="pdfUploaded && !pdfHasError && !pdfProcessing" class="import-file-upload__upload-success">
            <BaseIcon icon-name="check" class="import-file-upload__upload-success-icon" />
            <span class="import-file-upload__upload-success-text">
              {{ pdfData.totalFiles }} PDF files uploaded
              <span v-if="pdfData.matchedFiles.length > 0" class="import-file-upload__match-info">
                ({{ pdfData.matchedFiles.length }} matched)
              </span>
            </span>
          </div>

          <!-- PDF Error Display -->
          <div v-if="pdfHasError" class="import-file-upload__error">
            <BaseIcon icon-name="danger" class="import-file-upload__error-icon" />
            <div class="import-file-upload__error-content">
              <h4>PDF Processing Error</h4>
              <p>{{ pdfErrorMessage }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Summary Sidebar -->
      <div class="import-file-upload__sidebar"
        :style="{ visibility: bibUploaded || pdfUploaded ? 'visible' : 'hidden' }">
        <h4 class="import-file-upload__sidebar-title">Summary status:</h4>

        <div class="import-file-upload__sidebar-stats">
          <!-- Bibliography Status -->
          <div v-if="bibUploaded && !bibHasError" class="import-file-upload__sidebar-stat">
            <BaseIcon icon-name="document"
              class="import-file-upload__sidebar-stat-icon import-file-upload__sidebar-stat-icon--bib" />
            <span class="import-file-upload__sidebar-stat-text">{{ bibData.parsedEntries.length }} references
              found</span>
          </div>

          <!-- PDF Status -->
          <div v-if="pdfUploaded && !pdfHasError && !pdfProcessing" class="import-file-upload__sidebar-stat">
            <BaseIcon icon-name="import"
              class="import-file-upload__sidebar-stat-icon import-file-upload__sidebar-stat-icon--pdf" />
            <span class="import-file-upload__sidebar-stat-text">{{ pdfData.totalFiles }} PDF files uploaded</span>
          </div>

          <!-- Matching Status -->
          <div v-if="pdfUploaded && !pdfHasError && !pdfProcessing && pdfData.matchedFiles.length > 0"
            class="import-file-upload__sidebar-stat">
            <BaseIcon icon-name="check"
              class="import-file-upload__sidebar-stat-icon import-file-upload__sidebar-stat-icon--match" />
            <span class="import-file-upload__sidebar-stat-text">
              {{ pdfData.matchedFiles.length }} matched, {{ pdfData.unmatchedFiles.length }} mismatch{{
                pdfData.unmatchedFiles.length === 1 ? "" : "es"
              }}
              detected
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { useResolve } from "ts-injecty";
import type { CSVConfig } from "~/v1/domain/services/IFileService";
import { FileService } from "~/v1/domain/services/FileService";
import { PdfMatchingService } from "~/v1/domain/services/PdfMatchingService";
import "assets/icons/check";
import "assets/icons/danger";
import "assets/icons/document";
import "assets/icons/import";
import "assets/icons/info";
import "assets/icons/unavailable";

export default {
  name: "ImportFileUpload",

  props: {
    // Props to receive existing data when navigating back to this step
    initialBibData: {
      type: Object,
      default: () => ({
        fileName: "",
        parsedEntries: [],
        dataframeData: null,
        rawContent: "",
      }),
    },
    initialPdfData: {
      type: Object,
      default: () => ({
        matchedFiles: [],
        unmatchedFiles: [],
        totalFiles: 0,
      }),
    },
  },

  setup() {
    const fileService = useResolve(FileService);
    const pdfMatchingService = useResolve(PdfMatchingService);

    return {
      fileService,
      pdfMatchingService,
    };
  },

  data() {
    return {
      // Internal flag to prevent recursive updates during initialization
      isInitializing: false,

      // Bibliography state
      bibDragOver: false,
      bibUploaded: false,
      bibHasError: false,
      bibErrorMessage: "",
      bibData: {
        fileName: "",
        parsedEntries: [],
        dataframeData: null,
        rawContent: "",
      },

      // CSV parsing state
      showCsvColumnSelection: false,
      csvRawData: null,
      csvColumns: [],
      csvPreviewData: [],
      csvConfig: {
        referenceColumn: "",
        filesColumn: "",
      },

      // PDF state
      pdfDragOver: false,
      pdfUploaded: false,
      pdfHasError: false,
      pdfErrorMessage: "",
      pdfProcessing: false,
      pdfProcessedFiles: 0,
      pdfTotalFiles: 0,
      pdfData: {
        matchedFiles: [],
        unmatchedFiles: [],
        totalFiles: 0,
      },
    };
  },

  mounted() {
    // Initialize with existing data if provided
    this.initializeWithExistingData();
  },

  computed: {
    getBibDropzoneIcon() {
      if (this.bibHasError) return "danger";
      if (this.bibUploaded) return "check";
      return "document";
    },

    getBibDropzoneText() {
      if (this.bibHasError) return "Error parsing bibliography file";
      if (this.bibUploaded) return "Upload BibTeX File";
      return "Upload BibTeX File";
    },

    getPdfDropzoneIcon() {
      if (this.pdfHasError) return "danger";
      if (this.pdfUploaded) return "check";
      return "import";
    },

    getPdfDropzoneText() {
      if (this.pdfHasError) return "Error processing PDF files";
      if (this.pdfUploaded) return "Upload PDF Files";
      return "Upload PDF Files";
    },

    pdfProgressPercentage() {
      if (this.pdfTotalFiles === 0) return 0;
      return Math.round((this.pdfProcessedFiles / this.pdfTotalFiles) * 100);
    },

    isValid() {
      return (
        this.bibUploaded &&
        this.pdfUploaded &&
        !this.bibHasError &&
        !this.pdfHasError &&
        !this.pdfProcessing &&
        !this.showCsvColumnSelection &&
        this.bibData.parsedEntries.length > 0 &&
        this.pdfData.matchedFiles.length > 0
      );
    },
  },

  watch: {
    initialBibData: {
      handler(newData, oldData) {
        // Only initialize if data has actually changed and we're not already initializing
        if (!this.isInitializing && newData && (newData.fileName || newData.parsedEntries.length > 0)) {
          // Check if the data is actually different to avoid unnecessary updates
          const hasChanged = !oldData ||
            newData.fileName !== oldData.fileName ||
            newData.parsedEntries.length !== oldData.parsedEntries.length;

          if (hasChanged) {
            this.initializeWithExistingData();
          }
        }
      },
      deep: true,
      immediate: true,
    },

    initialPdfData: {
      handler(newData, oldData) {
        // Only initialize if data has actually changed and we're not already initializing
        if (!this.isInitializing && newData && (newData.matchedFiles.length > 0 || newData.unmatchedFiles.length > 0)) {
          // Check if the data is actually different to avoid unnecessary updates
          const hasChanged = !oldData ||
            newData.matchedFiles.length !== oldData.matchedFiles.length ||
            newData.unmatchedFiles.length !== oldData.unmatchedFiles.length ||
            newData.totalFiles !== oldData.totalFiles;

          if (hasChanged) {
            this.initializeWithExistingData();
          }
        }
      },
      deep: true,
      immediate: true,
    },

    bibData: {
      handler() {
        // Only emit updates if we're not in the middle of initializing
        if (!this.isInitializing) {
          this.emitBibUpdate();
          if (this.bibUploaded && this.pdfUploaded) {
            this.performFileMatching();
          }
        }
      },
      deep: true,
    },

    pdfData: {
      handler() {
        // Only emit updates if we're not in the middle of initializing
        if (!this.isInitializing) {
          this.emitPdfUpdate();
        }
      },
      deep: true,
    },
  },

  methods: {
    triggerBibFileInput() {
      this.$refs.bibFileInput.click();
    },

    handleBibDragOver(event) {
      event.preventDefault();
      this.bibDragOver = true;
    },

    handleBibDragLeave() {
      this.bibDragOver = false;
    },

    handleBibDrop(event) {
      event.preventDefault();
      this.bibDragOver = false;

      const files = event.dataTransfer.files;
      if (files.length > 0) {
        this.processBibFile(files[0]);
      }
    },

    handleBibFileSelect(event) {
      const files = event.target.files;
      if (files.length > 0) {
        this.processBibFile(files[0]);
      }
    },

    async processBibFile(file: File) {
      // Reset bib state
      this.bibHasError = false;
      this.bibErrorMessage = "";
      this.bibData = {
        fileName: "",
        parsedEntries: [],
        dataframeData: null,
        rawContent: "",
      };

      // Reset CSV state
      this.showCsvColumnSelection = false;
      this.csvRawData = null;
      this.csvColumns = [];
      this.csvPreviewData = [];
      this.csvConfig = {
        referenceColumn: "",
        filesColumn: "",
      };

      // Validate file type
      if (!this.fileService.isValidFileType(file, [".bib", ".bibtex", ".csv"])) {
        this.showBibError("Invalid file type. Please upload a .bib, .bibtex, or .csv file.");
        return;
      }

      this.bibData.fileName = file.name;

      try {
        // Read file content
        const content = await this.fileService.readFileContent(file);
        this.bibData.rawContent = content;

        if (this.isCsvFile(file)) {
          // Handle CSV file
          await this.parseCsvContent(content);
        } else if (this.isBibTexFile(file)) {
          // Handle BibTeX file
          const result = await this.fileService.parseBibTeX(content);
          this.bibData.parsedEntries = result.entries;
          this.bibData.dataframeData = result.dataframeData;

          if (this.bibData.parsedEntries.length > 0) {
            this.bibUploaded = true;
          } else {
            this.showBibError("No valid BibTeX entries found in the file.");
          }
        }
      } catch (error) {
        this.showBibError(`Failed to process file: ${error.message}`);
      }
    },

    isCsvFile(file: File) {
      return file.name.toLowerCase().endsWith(".csv");
    },

    isBibTexFile(file: File) {
      const fileName = file.name.toLowerCase();
      return fileName.endsWith(".bib") || fileName.endsWith(".bibtex");
    },

    async parseCsvContent(content) {
      try {
        const previewData = await this.fileService.parseCSVForPreview(content);

        // Store CSV data for column selection
        this.csvRawData = previewData.rawData;
        this.csvColumns = previewData.columns;
        this.csvPreviewData = previewData.previewRows;

        // Show column selection UI
        this.showCsvColumnSelection = true;

      } catch (error) {
        throw new Error(`CSV parsing failed: ${error.message}`);
      }
    },

    async processCsvWithConfig() {
      try {
        if (!this.csvConfig.referenceColumn) {
          this.showBibError("Please select a reference column to continue.");
          return;
        }

        if (!this.csvRawData || this.csvRawData.length === 0) {
          this.showBibError("No CSV data available. Please upload a file first.");
          return;
        }

        const config: CSVConfig = {
          referenceColumn: this.csvConfig.referenceColumn,
          filesColumn: this.csvConfig.filesColumn || undefined,
        };

        const result = await this.fileService.parseCSVWithConfig(this.csvRawData, config);

        this.bibData.parsedEntries = result.entries;
        this.bibData.dataframeData = result.dataframeData;

        // Hide column selection and mark as uploaded
        this.showCsvColumnSelection = false;
        this.bibUploaded = true;

      } catch (error) {
        this.showBibError(`Failed to process CSV data: ${error.message}`);
      }
    },



    cancelCsvSelection() {
      // Reset CSV state and clear upload
      this.showCsvColumnSelection = false;
      this.csvRawData = null;
      this.csvColumns = [];
      this.csvPreviewData = [];
      this.csvConfig = {
        referenceColumn: "",
        filesColumn: "",
      };

      // Reset bib data
      this.bibData = {
        fileName: "",
        parsedEntries: [],
        dataframeData: null,
        rawContent: "",
      };
      this.bibUploaded = false;
      this.bibHasError = false;
      this.bibErrorMessage = "";
    },



    showBibError(message) {
      this.bibHasError = true;
      this.bibErrorMessage = message;
      this.bibUploaded = false;
    },

    // PDF methods
    triggerPdfFolderInput() {
      this.$refs.pdfFolderInput.click();
    },

    handlePdfDragOver(event) {
      event.preventDefault();
      this.pdfDragOver = true;
    },

    handlePdfDragLeave() {
      this.pdfDragOver = false;
    },

    handlePdfDrop(event) {
      event.preventDefault();
      this.pdfDragOver = false;

      const files = Array.from(event.dataTransfer.files);
      this.processPdfFiles(files);
    },

    handlePdfFolderSelect(event) {
      const files = Array.from(event.target.files);
      this.processPdfFiles(files);
    },

    async processPdfFiles(files: File[]) {
      // Reset PDF error state but preserve existing files for additive upload
      this.pdfHasError = false;
      this.pdfErrorMessage = "";

      // Get existing files to merge with new ones
      const existingFiles = [
        ...this.pdfData.matchedFiles.map(mf => mf.file),
        ...this.pdfData.unmatchedFiles
      ];

      this.pdfProcessedFiles = 0;

      const pdfFiles = files.filter((file) => this.isValidPdfFile(file));

      if (pdfFiles.length === 0) {
        this.showPdfError("No valid PDF files found. Please select a folder containing PDF files.");
        return;
      }

      this.pdfTotalFiles = pdfFiles.length;
      this.pdfProcessing = true;
      this.clearPdfError(); // Clear any previous errors

      const validFiles: File[] = [];
      const fileErrors: string[] = [];

      for (const file of pdfFiles) {
        // Skip files that are already uploaded (by name)
        const isDuplicate = existingFiles.some(existingFile => existingFile.name === file.name);
        if (!isDuplicate) {
          const result = await this.validatePdfFile(file);
          if (result.valid) {
            validFiles.push(file);
          } else {
            fileErrors.push(`${file.name}: ${result.error}`);
          }
        }
        this.pdfProcessedFiles++;
      }

      // Combine existing files with new valid files
      const allFiles = [...existingFiles, ...validFiles];
      this.pdfData.totalFiles = allFiles.length;

      // Re-run file matching with all files (existing + new)
      this.performFileMatching(allFiles);

      this.pdfProcessing = false;

      // Show errors if any files failed, but don't fail the entire process
      if (fileErrors.length > 0) {
        const successCount = validFiles.length;
        const errorCount = fileErrors.length;
        const totalCount = successCount + errorCount;

        let errorMessage = `Processed ${successCount} of ${totalCount} files successfully.\n\n`;
        errorMessage += `Files that could not be processed:\n${fileErrors.join('\n')}`;

        this.showPdfError(errorMessage);
      } else {
        this.pdfUploaded = true;
        this.pdfHasError = false;
        this.pdfErrorMessage = "";
      }
    },

    async validatePdfFile(file: File) {
      const maxSize = 200 * 1024 * 1024; // 200MB
      if (file.size > maxSize) {
        return { valid: false, error: `File ${file.name} is too large (max 200MB)` };
      } else if (file.size === 0) {
        return { valid: false, error: `File ${file.name} is empty` };
      }

      return { valid: true };
    },

    isValidPdfFile(file: File) {
      return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
    },


    performFileMatching(uploadedFiles: File[] | null = null) {
      const filesToMatch: File[] =
        uploadedFiles || this.pdfData.matchedFiles.concat(this.pdfData.unmatchedFiles).map((item) => item.file || item);

      if (!this.bibData.parsedEntries || this.bibData.parsedEntries.length === 0 || filesToMatch.length === 0) {
        return;
      }

      const result = this.pdfMatchingService.matchFiles(filesToMatch, this.bibData.parsedEntries);

      this.pdfData.matchedFiles = result.matchedFiles;
      this.pdfData.unmatchedFiles = result.unmatchedFiles;
    },



    showPdfError(message) {
      this.pdfHasError = true;
      this.pdfErrorMessage = message;
      this.pdfUploaded = false;
    },

    clearPdfError() {
      this.pdfHasError = false;
      this.pdfErrorMessage = "";
    },

    // Event emitters
    emitBibUpdate() {
      this.$emit("bib-update", {
        isValid: this.bibUploaded && !this.bibHasError && this.bibData.parsedEntries.length > 0,
        fileName: this.bibData.fileName,
        parsedEntries: this.bibData.parsedEntries,
        dataframeData: this.bibData.dataframeData,
        rawContent: this.bibData.rawContent,
      });
    },

    emitPdfUpdate() {
      this.$emit("pdf-update", {
        isValid: this.pdfUploaded && !this.pdfHasError && this.pdfData.matchedFiles.length > 0,
        matchedFiles: this.pdfData.matchedFiles,
        unmatchedFiles: this.pdfData.unmatchedFiles,
        totalFiles: this.pdfData.totalFiles,
        hasError: this.pdfHasError,
        errorMessage: this.pdfErrorMessage,
      });
    },

    // Initialize component with existing data when navigating back
    initializeWithExistingData() {
      // Set flag to prevent recursive updates
      this.isInitializing = true;

      // Initialize bibliography data
      if (this.initialBibData && (this.initialBibData.fileName || this.initialBibData.parsedEntries.length > 0)) {
        this.bibData = {
          fileName: this.initialBibData.fileName || "",
          parsedEntries: this.initialBibData.parsedEntries || [],
          dataframeData: this.initialBibData.dataframeData || null,
          rawContent: this.initialBibData.rawContent || "",
        };
        this.bibUploaded = this.bibData.parsedEntries.length > 0;
        this.bibHasError = false;
        this.bibErrorMessage = "";

        // Ensure CSV selection is hidden when initializing with existing data
        this.showCsvColumnSelection = false;
      }

      // Initialize PDF data
      if (this.initialPdfData && (this.initialPdfData.matchedFiles.length > 0 || this.initialPdfData.unmatchedFiles.length > 0 || this.initialPdfData.totalFiles > 0)) {
        this.pdfData = {
          matchedFiles: this.initialPdfData.matchedFiles || [],
          unmatchedFiles: this.initialPdfData.unmatchedFiles || [],
          totalFiles: this.initialPdfData.totalFiles || 0,
        };
        this.pdfUploaded = this.pdfData.totalFiles > 0;
        this.pdfHasError = false;
        this.pdfErrorMessage = "";
        this.pdfProcessing = false;
      }

      // Clear the initialization flag and emit updates after all data is set
      this.$nextTick(() => {
        this.isInitializing = false;
        // Emit updates to parent to ensure consistency
        this.emitBibUpdate();
        this.emitPdfUpdate();
      });
    },

    // Public methods for parent components
    reset() {
      // Set flag to prevent recursive updates during reset
      this.isInitializing = true;

      // Reset bibliography state
      this.bibDragOver = false;
      this.bibUploaded = false;
      this.bibHasError = false;
      this.bibErrorMessage = "";
      this.bibData = {
        fileName: "",
        parsedEntries: [],
        dataframeData: null,
        rawContent: "",
      };

      // Reset CSV state
      this.showCsvColumnSelection = false;
      this.csvRawData = null;
      this.csvColumns = [];
      this.csvPreviewData = [];
      this.csvConfig = {
        referenceColumn: "",
        filesColumn: "",
      };

      // Reset PDF state
      this.pdfDragOver = false;
      this.pdfUploaded = false;
      this.pdfHasError = false;
      this.pdfErrorMessage = "";
      this.pdfProcessing = false;
      this.pdfProcessedFiles = 0;
      this.pdfTotalFiles = 0;
      this.pdfData = {
        matchedFiles: [],
        unmatchedFiles: [],
        totalFiles: 0,
      };

      // Clear the initialization flag and emit updates after reset
      this.$nextTick(() => {
        this.isInitializing = false;
        this.emitBibUpdate();
        this.emitPdfUpdate();
      });
    },
  },
};
</script>
<style lang="scss" scoped>
.import-file-upload {
  padding: $base-space * 3;

  &__header {
    text-align: center;
    margin-bottom: $base-space * 3;
  }

  &__title {
    font-size: 1.5rem;
    font-weight: 600;
    margin-bottom: $base-space;
    color: var(--fg-primary);
  }

  &__description {
    color: var(--fg-secondary);
    margin-bottom: 0;
  }

  &__content {
    display: flex;
    gap: $base-space * 3;

    @media (max-width: 768px) {
      flex-direction: column;
    }
  }

  &__main {
    flex: 2;
    display: flex;
    flex-direction: column;
    gap: $base-space * 3;
  }

  &__sidebar {
    flex: 1;
    background: var(--bg-accent-grey-1);
    border: 1px solid var(--border-field);
    border-radius: $border-radius-m;
    padding: $base-space * 2;
    height: fit-content;
    position: sticky;
    top: $base-space * 2;
  }

  &__section {
    display: flex;
    flex-direction: column;
    gap: $base-space * 2;
  }

  &__section-header {
    margin-bottom: $base-space * 2;
  }

  &__section-title {
    font-size: 1.2rem;
    font-weight: 600;
    margin-bottom: $base-space;
    color: var(--fg-primary);
  }

  &__section-icon {
    font-size: 1.2rem;
    color: var(--fg-secondary);
  }

  &__section-description {
    color: var(--fg-secondary);
    font-size: 0.9rem;
    margin-bottom: 0;
    line-height: 1.4;
  }

  &__dropzone {
    border: 2px dashed var(--border-field);
    border-radius: $border-radius-m;
    padding: $base-space * 4 $base-space * 3;
    text-align: center;
    cursor: pointer;
    transition: $swift-ease-out;
    background: var(--bg-accent-grey-1);

    &:hover {
      border-color: var(--bg-action);
      background: var(--bg-accent-grey-2);
    }

    &--dragover {
      border-color: var(--bg-action);
      background: var(--bg-accent-grey-2);
      transform: scale(1.02);
    }

    &--error {
      border-color: var(--color-danger);
      background: var(--bg-banner-error);
    }

    &--success {
      border-color: var(--color-success);
      background: var(--bg-solid-grey-2);
    }
  }

  &__dropzone-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: $base-space;
  }

  &__dropzone-icon {
    font-size: 3rem;
    color: var(--fg-secondary);
  }

  &__dropzone-text {
    font-size: 1.1rem;
    font-weight: 500;
    color: var(--fg-primary);
    margin: 0;
  }

  &__dropzone-subtext {
    font-size: 0.9rem;
    color: var(--fg-secondary);
    margin: 0;
  }

  &__dropzone-buttons {
    display: flex;
    gap: $base-space;
    margin-top: $base-space;
  }

  &__progress {
    padding: $base-space * 2;
    background: var(--bg-accent-grey-2);
    border-radius: $border-radius;
    border: 1px solid var(--border-field);
  }

  &__progress-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: $base-space;

    h4 {
      margin: 0;
      font-size: 1rem;
      color: var(--fg-primary);
    }

    span {
      font-size: 0.9rem;
      color: var(--fg-secondary);
    }
  }

  &__progress-bar {
    width: 100%;
    height: 8px;
    background: var(--bg-accent-grey-3);
    border-radius: $border-radius-s;
    overflow: hidden;
  }

  &__progress-fill {
    height: 100%;
    background: var(--bg-action);
    border-radius: $border-radius-s;
    transition: width 0.3s ease;
  }

  &__success {
    display: flex;
    align-items: center;
    gap: $base-space;
    padding: $base-space * 2;
    background: var(--bg-solid-grey-2);
    border: 1px solid var(--color-success);
    border-radius: $border-radius;
  }

  &__success-icon {
    color: var(--color-success);
    font-size: 1.2rem;
  }

  &__success-content h4 {
    margin: 0 0 calc($base-space / 2) 0;
    color: var(--color-success);
    font-size: 1rem;
  }

  &__success-content p {
    margin: 0;
    color: var(--fg-primary);
  }

  &__error {
    display: flex;
    align-items: flex-start;
    gap: $base-space;
    padding: $base-space * 2;
    background: var(--bg-banner-error);
    border: 1px solid var(--color-danger);
    border-radius: $border-radius;
  }

  &__error-icon {
    color: var(--color-danger);
    font-size: 1.2rem;
    margin-top: 0.1rem;
  }

  &__error-content h4 {
    margin: 0 0 $base-space 0;
    color: var(--color-danger);
    font-size: 1rem;
  }

  &__error-content p {
    margin: 0;
    color: var(--fg-primary);
  }

  &__upload-success {
    display: flex;
    align-items: center;
    gap: $base-space;
    padding: $base-space;
    background: var(--bg-solid-grey-2);
    border: 1px solid var(--color-success);
    border-radius: $border-radius;
    margin-top: $base-space;
  }

  &__upload-success-icon {
    color: var(--color-success);
    font-size: 1rem;
    flex-shrink: 0;
  }

  &__upload-success-text {
    color: var(--fg-primary);
    font-size: 0.9rem;
    font-weight: 500;
  }

  &__match-info {
    color: var(--color-success);
    font-weight: 600;
  }

  &__sidebar-title {
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: $base-space * 2;
    color: var(--fg-primary);
  }

  &__sidebar-stats {
    display: flex;
    flex-direction: column;
    gap: $base-space * 2;
    margin-bottom: $base-space * 3;
  }

  &__sidebar-stat {
    display: flex;
    align-items: flex-start;
    gap: $base-space;
  }

  &__sidebar-stat-icon {
    font-size: 1.2rem;
    margin-top: 0.1rem;
    flex-shrink: 0;

    &--bib {
      color: var(--color-danger);
    }

    &--pdf {
      color: var(--fg-secondary);
    }

    &--match {
      color: var(--color-success);
    }
  }

  &__sidebar-stat-text {
    color: var(--fg-primary);
    font-size: 0.9rem;
    line-height: 1.4;
  }

  &__sidebar-action {
    margin-top: auto;
    padding-top: $base-space * 2;
    border-top: 1px solid var(--border-field);
  }

  &__preview-title {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: $base-space * 2;
    color: var(--fg-primary);
    text-align: center;
  }

  &__stats {
    display: flex;
    justify-content: center;
    gap: $base-space * 2;
    margin-bottom: $base-space * 3;
    flex-wrap: wrap;
  }

  &__stat {
    display: flex;
    align-items: center;
    gap: $base-space;
    padding: $base-space;
    background: var(--bg-accent-grey-2);
    border-radius: $border-radius;
    border: 1px solid var(--border-field);

    &--success {
      border-color: var(--color-success);
      background: var(--bg-solid-grey-2);
    }

    &--warning {
      border-color: var(--color-warning);
      background: var(--bg-banner-warning);
    }
  }

  &__stat-icon {
    font-size: 1.2rem;
    color: var(--fg-secondary);

    .import-file-upload__stat--success & {
      color: var(--color-success);
    }

    .import-file-upload__stat--warning & {
      color: var(--color-warning);
    }
  }

  &__stat-content {
    display: flex;
    flex-direction: column;
    gap: calc($base-space / 4);
  }

  &__stat-value {
    font-size: 1.2rem;
    font-weight: 600;
    color: var(--fg-primary);
  }

  &__stat-label {
    font-size: 0.9rem;
    color: var(--fg-secondary);
  }

  &__quick-preview {
    margin-top: $base-space * 2;
  }

  &__quick-preview-title {
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: $base-space * 2;
    color: var(--fg-primary);
  }

  &__table-container {
    overflow-x: auto;
    border: 1px solid var(--border-field);
    border-radius: $border-radius;
  }

  &__table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;

    th {
      background: var(--bg-accent-grey-2);
      padding: $base-space;
      text-align: left;
      font-weight: 600;
      color: var(--fg-primary);
      border-bottom: 1px solid var(--border-field);
    }

    td {
      padding: $base-space;
      border-bottom: 1px solid var(--border-field);
      color: var(--fg-primary);
      max-width: 200px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    tr:last-child td {
      border-bottom: none;
    }

    tr:hover {
      background: var(--bg-accent-grey-3);
    }
  }

  &__table-cell {
    &--key {
      font-family: $quaternary-font-family;
      font-weight: 600;
      color: var(--bg-action);
    }

    &--title {
      font-weight: 500;
      max-width: 250px;
    }

    &--filename {
      display: flex;
      align-items: center;
      gap: calc($base-space / 2);
      font-weight: 500;
      max-width: 200px;
    }

    &--match {
      text-align: center;
    }
  }

  &__file-icon {
    color: var(--color-danger);
    font-size: 1rem;
    flex-shrink: 0;
  }

  &__match-badge {
    display: inline-block;
    padding: calc($base-space / 4) calc($base-space / 2);
    border-radius: $border-radius-s;
    font-size: 0.8rem;
    font-weight: 500;
    text-transform: uppercase;

    &--exact {
      background: var(--color-success);
      color: white;
    }

    &--partial {
      background: var(--bg-action);
      color: white;
    }

    &--file_field {
      background: var(--bg-action);
      color: white;
    }

    &--title {
      background: var(--color-warning);
      color: white;
    }
  }

  &__preview-note {
    margin-top: $base-space * 2;
    text-align: center;

    p {
      margin: 0;
      font-size: 0.9rem;
      color: var(--fg-secondary);
      font-style: italic;
    }
  }

  // CSV Column Selection Styles
  &__csv-selection {
    margin-top: $base-space * 2;
    padding: $base-space * 2;
    background: var(--bg-accent-grey-2);
    border: 1px solid var(--border-field);
    border-radius: $border-radius;
  }

  &__csv-selection-header {
    margin-bottom: $base-space * 2;
  }

  &__csv-selection-title {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: $base-space;
    color: var(--fg-primary);
  }

  &__csv-selection-description {
    color: var(--fg-secondary);
    font-size: 0.9rem;
    margin-bottom: 0;
    line-height: 1.4;
  }

  &__csv-columns {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: $base-space * 2;
    margin-bottom: $base-space * 2;

    @media (max-width: 768px) {
      grid-template-columns: 1fr;
    }
  }

  &__csv-column-group {
    display: flex;
    flex-direction: column;
    gap: calc($base-space / 2);
  }

  &__csv-column-label {
    font-size: 0.9rem;
    font-weight: 500;
    color: var(--fg-primary);
    display: flex;
    flex-direction: column;
    gap: calc($base-space / 2);
  }

  &__csv-column-select {
    padding: calc($base-space / 2) $base-space;
    border: 1px solid var(--border-field);
    border-radius: $border-radius-s;
    background: var(--bg-solid-grey-1);
    color: var(--fg-primary);
    font-size: 0.9rem;

    &:focus {
      outline: none;
      border-color: var(--bg-action);
      box-shadow: 0 0 0 2px var(--bg-action-alpha);
    }
  }

  &__csv-column-help {
    font-size: 0.8rem;
    color: var(--fg-secondary);
    margin: 0;
    line-height: 1.3;
  }

  &__csv-preview {
    margin-bottom: $base-space * 2;

    h5 {
      font-size: 0.9rem;
      font-weight: 600;
      margin-bottom: $base-space;
      color: var(--fg-primary);
    }
  }

  &__csv-preview-table {
    overflow-x: auto;
    border: 1px solid var(--border-field);
    border-radius: $border-radius-s;
    background: var(--bg-solid-grey-1);
  }

  &__csv-preview-header--selected {
    background: var(--bg-action-alpha) !important;
    color: var(--bg-action) !important;
    font-weight: 600;
    position: relative;
  }

  &__csv-preview-cell--selected {
    background: var(--bg-action-alpha) !important;
    font-weight: 500;
  }

  &__csv-preview-badge {
    display: inline-block;
    padding: 2px 6px;
    background: var(--bg-action);
    color: white;
    font-size: 0.7rem;
    font-weight: 600;
    border-radius: $border-radius-s;
    margin-left: calc($base-space / 2);
    text-transform: uppercase;
  }

  &__csv-actions {
    display: flex;
    gap: $base-space;
    justify-content: flex-end;

    @media (max-width: 768px) {
      flex-direction: column;
    }
  }
}
</style>
