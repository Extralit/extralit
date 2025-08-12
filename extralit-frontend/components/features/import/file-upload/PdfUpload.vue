<template>
  <div class="pdf-upload">
    <div class="pdf-upload__section-header">
      <h3 class="pdf-upload__section-title">Step 2: Upload Full-Text PDFs</h3>
      <p class="pdf-upload__section-description">
        Upload the PDF files that correspond to the references in your .bib file.<br />
        Extralit will match them automatically for extraction.
      </p>
    </div>

    <div class="pdf-upload__dropzone" :class="{
      'pdf-upload__dropzone--dragover': dragOver,
      'pdf-upload__dropzone--error': hasError,
      'pdf-upload__dropzone--success': uploaded,
    }" @drop="handleDrop" @dragover="handleDragOver" @dragleave="handleDragLeave"
      @click="triggerFolderInput">
      <input ref="folderInput" type="file" accept=".pdf" multiple webkitdirectory style="display: none"
        @change="handleFolderSelect" />

      <div class="pdf-upload__dropzone-content">
        <BaseIcon :icon-name="getDropzoneIcon" class="pdf-upload__dropzone-icon" />
        <p class="pdf-upload__dropzone-text">
          {{ getDropzoneText }}
        </p>
        <p class="pdf-upload__dropzone-subtext">Upload a folder containing your PDF files.<br /></p>
      </div>
    </div>

    <!-- Processing Progress -->
    <div v-if="processing" class="pdf-upload__progress">
      <div class="pdf-upload__progress-header">
        <h4>Processing PDF Files...</h4>
        <span>{{ processedFiles }}/{{ totalFiles }} files</span>
      </div>
      <div class="pdf-upload__progress-bar">
        <div class="pdf-upload__progress-fill" :style="{ width: `${progressPercentage}%` }"></div>
      </div>
    </div>

    <!-- Success Display -->
    <div v-if="uploaded && !hasError && !processing" class="pdf-upload__upload-success">
      <BaseIcon icon-name="check" class="pdf-upload__upload-success-icon" />
      <span class="pdf-upload__upload-success-text">
        {{ data.totalFiles }} PDF files uploaded
        <span v-if="data.matchedFiles.length > 0" class="pdf-upload__match-info">
          ({{ data.matchedFiles.length }} matched)
        </span>
      </span>
    </div>

    <!-- Error Display -->
    <div v-if="hasError" class="pdf-upload__error">
      <BaseIcon icon-name="danger" class="pdf-upload__error-icon" />
      <div class="pdf-upload__error-content">
        <h4>PDF Processing Error</h4>
        <p>{{ errorMessage }}</p>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { useResolve } from "ts-injecty";
import { PdfMatchingService } from "~/v1/domain/services/FileMatchingService";
import "assets/icons/check";
import "assets/icons/danger";
import "assets/icons/import";

interface PdfData {
  matchedFiles: any[];
  unmatchedFiles: any[];
  totalFiles: number;
}

export default {
  name: "PdfUpload",

  props: {
    initialData: {
      type: Object as () => PdfData,
      default: () => ({
        matchedFiles: [],
        unmatchedFiles: [],
        totalFiles: 0,
      }),
    },
    bibliographyEntries: {
      type: Array,
      default: () => [],
    },
  },

  emits: ["update"],

  setup() {
    const pdfMatchingService = useResolve(PdfMatchingService);
    return { pdfMatchingService };
  },

  data() {
    return {
      dragOver: false,
      uploaded: false,
      hasError: false,
      errorMessage: "",
      processing: false,
      processedFiles: 0,
      totalFiles: 0,
      data: {
        matchedFiles: [],
        unmatchedFiles: [],
        totalFiles: 0,
      } as PdfData,
    };
  },

  mounted() {
    this.initializeWithExistingData();
  },

  computed: {
    getDropzoneIcon(): string {
      if (this.hasError) return "danger";
      if (this.uploaded) return "check";
      return "import";
    },

    getDropzoneText(): string {
      if (this.hasError) return "Error processing PDF files";
      if (this.uploaded) return "Upload PDF Files";
      return "Upload PDF Files";
    },

    progressPercentage(): number {
      if (this.totalFiles === 0) return 0;
      return Math.round((this.processedFiles / this.totalFiles) * 100);
    },
  },

  watch: {
    initialData: {
      handler(newData: PdfData) {
        if (newData && (newData.matchedFiles.length > 0 || newData.unmatchedFiles.length > 0 || newData.totalFiles > 0)) {
          this.initializeWithExistingData();
        }
      },
      deep: true,
      immediate: true,
    },
  },

  methods: {
    triggerFolderInput(): void {
      (this.$refs.folderInput as HTMLInputElement).click();
    },

    handleDragOver(event: DragEvent): void {
      event.preventDefault();
      this.dragOver = true;
    },

    handleDragLeave(): void {
      this.dragOver = false;
    },

    handleDrop(event: DragEvent): void {
      event.preventDefault();
      this.dragOver = false;

      const files = Array.from(event.dataTransfer?.files || []);
      this.processFiles(files);
    },

    handleFolderSelect(event: Event): void {
      const target = event.target as HTMLInputElement;
      const files = Array.from(target.files || []);
      this.processFiles(files);
    },

    async processFiles(files: File[]): Promise<void> {
      // Reset error state but preserve existing files for additive upload
      this.hasError = false;
      this.errorMessage = "";

      // Get existing files to merge with new ones
      const existingFiles = [
        ...this.data.matchedFiles.map(mf => mf.file),
        ...this.data.unmatchedFiles
      ];

      this.processedFiles = 0;

      const pdfFiles = files.filter((file) => this.isValidPdfFile(file));

      if (pdfFiles.length === 0) {
        this.showError("No valid PDF files found. Please select a folder containing PDF files.");
        return;
      }

      this.totalFiles = pdfFiles.length;
      this.processing = true;
      this.clearError();

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
        this.processedFiles++;
      }

      // Combine existing files with new valid files
      const allFiles = [...existingFiles, ...validFiles];
      this.data.totalFiles = allFiles.length;

      // Re-run file matching with all files (existing + new)
      this.performFileMatching(allFiles);

      this.processing = false;

      // Show errors if any files failed, but don't fail the entire process
      if (fileErrors.length > 0) {
        const successCount = validFiles.length;
        const errorCount = fileErrors.length;
        const totalCount = successCount + errorCount;

        let errorMessage = `Processed ${successCount} of ${totalCount} files successfully.\n\n`;
        errorMessage += `Files that could not be processed:\n${fileErrors.join('\n')}`;

        this.showError(errorMessage);
      } else {
        this.uploaded = true;
        this.hasError = false;
        this.errorMessage = "";
      }

      this.emitUpdate();
    },

    async validatePdfFile(file: File): Promise<{ valid: boolean; error?: string }> {
      const maxSize = 200 * 1024 * 1024; // 200MB
      if (file.size > maxSize) {
        return { valid: false, error: `File ${file.name} is too large (max 200MB)` };
      } else if (file.size === 0) {
        return { valid: false, error: `File ${file.name} is empty` };
      }

      return { valid: true };
    },

    isValidPdfFile(file: File): boolean {
      return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
    },

    performFileMatching(uploadedFiles: File[]): void {
      if (!this.bibliographyEntries || this.bibliographyEntries.length === 0 || uploadedFiles.length === 0) {
        // If no bibliography entries, all files are unmatched
        this.data.matchedFiles = [];
        this.data.unmatchedFiles = uploadedFiles;
        return;
      }

      const result = this.pdfMatchingService.matchFiles(uploadedFiles, this.bibliographyEntries);

      this.data.matchedFiles = result.matchedFiles;
      this.data.unmatchedFiles = result.unmatchedFiles;
    },

    showError(message: string): void {
      this.hasError = true;
      this.errorMessage = message;
      this.uploaded = false;
    },

    clearError(): void {
      this.hasError = false;
      this.errorMessage = "";
    },

    initializeWithExistingData(): void {
      if (this.initialData && (this.initialData.matchedFiles.length > 0 || this.initialData.unmatchedFiles.length > 0 || this.initialData.totalFiles > 0)) {
        this.data = {
          matchedFiles: this.initialData.matchedFiles || [],
          unmatchedFiles: this.initialData.unmatchedFiles || [],
          totalFiles: this.initialData.totalFiles || 0,
        };
        this.uploaded = this.data.totalFiles > 0;
        this.hasError = false;
        this.errorMessage = "";
        this.processing = false;
      }
    },

    emitUpdate(): void {
      this.$emit("update", {
        isValid: this.uploaded && !this.hasError && this.data.matchedFiles.length > 0,
        matchedFiles: this.data.matchedFiles,
        unmatchedFiles: this.data.unmatchedFiles,
        totalFiles: this.data.totalFiles,
        hasError: this.hasError,
        errorMessage: this.errorMessage,
      });
    },

    reset(): void {
      this.dragOver = false;
      this.uploaded = false;
      this.hasError = false;
      this.errorMessage = "";
      this.processing = false;
      this.processedFiles = 0;
      this.totalFiles = 0;
      this.data = {
        matchedFiles: [],
        unmatchedFiles: [],
        totalFiles: 0,
      };
    },
  },
};
</script>

<style lang="scss" scoped>
.pdf-upload {
  display: flex;
  flex-direction: column;
  gap: $base-space * 2;
}

.pdf-upload__section-header {
  margin-bottom: $base-space * 2;
}

.pdf-upload__section-title {
  font-size: 1.2rem;
  font-weight: 600;
  margin-bottom: $base-space;
  color: var(--fg-primary);
}

.pdf-upload__section-description {
  color: var(--fg-secondary);
  font-size: 0.9rem;
  margin-bottom: 0;
  line-height: 1.4;
}

.pdf-upload__dropzone {
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

.pdf-upload__dropzone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $base-space;
}

.pdf-upload__dropzone-icon {
  font-size: 3rem;
  color: var(--fg-secondary);
}

.pdf-upload__dropzone-text {
  font-size: 1.1rem;
  font-weight: 500;
  color: var(--fg-primary);
  margin: 0;
}

.pdf-upload__dropzone-subtext {
  font-size: 0.9rem;
  color: var(--fg-secondary);
  margin: 0;
}

.pdf-upload__progress {
  padding: $base-space * 2;
  background: var(--bg-accent-grey-2);
  border-radius: $border-radius;
  border: 1px solid var(--border-field);
}

.pdf-upload__progress-header {
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

.pdf-upload__progress-bar {
  width: 100%;
  height: 8px;
  background: var(--bg-accent-grey-3);
  border-radius: $border-radius-s;
  overflow: hidden;
}

.pdf-upload__progress-fill {
  height: 100%;
  background: var(--bg-action);
  border-radius: $border-radius-s;
  transition: width 0.3s ease;
}

.pdf-upload__upload-success {
  display: flex;
  align-items: center;
  gap: $base-space;
  padding: $base-space;
  background: var(--bg-solid-grey-2);
  border: 1px solid var(--color-success);
  border-radius: $border-radius;
  margin-top: $base-space;
}

.pdf-upload__upload-success-icon {
  color: var(--color-success);
  font-size: 1rem;
  flex-shrink: 0;
}

.pdf-upload__upload-success-text {
  color: var(--fg-primary);
  font-size: 0.9rem;
  font-weight: 500;
}

.pdf-upload__match-info {
  color: var(--color-success);
  font-weight: 600;
}

.pdf-upload__error {
  display: flex;
  align-items: flex-start;
  gap: $base-space;
  padding: $base-space * 2;
  background: var(--bg-banner-error);
  border: 1px solid var(--color-danger);
  border-radius: $border-radius;
}

.pdf-upload__error-icon {
  color: var(--color-danger);
  font-size: 1.2rem;
  margin-top: 0.1rem;
}

.pdf-upload__error-content h4 {
  margin: 0 0 $base-space 0;
  color: var(--color-danger);
  font-size: 1rem;
}

.pdf-upload__error-content p {
  margin: 0;
  color: var(--fg-primary);
}
</style>
