<template>
  <div class="import-pdf-upload">
    <div class="import-pdf-upload__header">
      <h3 class="import-pdf-upload__title">Upload PDF Files</h3>
      <p class="import-pdf-upload__description">
        Upload PDF files to match with your bibliography entries
      </p>
    </div>

    <div class="import-pdf-upload__content">
      <!-- File Upload Section -->
      <div class="import-pdf-upload__file-section">
        <div
          class="import-pdf-upload__dropzone"
          :class="{
            'import-pdf-upload__dropzone--dragover': isDragOver,
            'import-pdf-upload__dropzone--error': hasError,
            'import-pdf-upload__dropzone--success': hasFiles,
          }"
          @drop="handleDrop"
          @dragover="handleDragOver"
          @dragleave="handleDragLeave"
          @click="triggerFileInput"
        >
          <input
            ref="fileInput"
            type="file"
            accept=".pdf"
            multiple
            webkitdirectory
            style="display: none"
            @change="handleFileSelect"
          />
          <input
            ref="multiFileInput"
            type="file"
            accept=".pdf"
            multiple
            style="display: none"
            @change="handleFileSelect"
          />

          <div class="import-pdf-upload__dropzone-content">
            <BaseIcon :icon-name="getDropzoneIcon" class="import-pdf-upload__dropzone-icon" />
            <p class="import-pdf-upload__dropzone-text">
              {{ getDropzoneText }}
            </p>
            <p class="import-pdf-upload__dropzone-subtext">
              Drop PDF files here or click to browse
            </p>
            <div class="import-pdf-upload__dropzone-buttons">
              <BaseButton class="secondary" @click.stop="selectMultipleFiles">
                Select Files
              </BaseButton>
              <BaseButton class="secondary" @click.stop="selectFolder">
                Select Folder
              </BaseButton>
            </div>
          </div>
        </div>

        <!-- Upload Progress -->
        <div v-if="isProcessing" class="import-pdf-upload__progress">
          <div class="import-pdf-upload__progress-header">
            <h4>Processing Files...</h4>
            <span>{{ processedFiles }}/{{ totalFiles }} files</span>
          </div>
          <div class="import-pdf-upload__progress-bar">
            <div
              class="import-pdf-upload__progress-fill"
              :style="{ width: `${progressPercentage}%` }"
            ></div>
          </div>
        </div>

        <!-- Error Display -->
        <div v-if="hasError" class="import-pdf-upload__error">
          <BaseIcon icon-name="danger" class="import-pdf-upload__error-icon" />
          <div class="import-pdf-upload__error-content">
            <h4>Upload Error</h4>
            <p>{{ errorMessage }}</p>
            <ul v-if="fileErrors.length > 0" class="import-pdf-upload__error-list">
              <li v-for="(error, index) in fileErrors" :key="index">
                {{ error }}
              </li>
            </ul>
          </div>
        </div>

        <!-- Summary Stats -->
        <div v-if="hasFiles && !isProcessing" class="import-pdf-upload__summary">
          <div class="import-pdf-upload__summary-header">
            <h4>File Matching Summary</h4>
            <BaseButton
              v-if="unmatchedFiles.length > 0"
              class="tertiary small"
              @click="showUnmatchedFiles = !showUnmatchedFiles"
            >
              {{ showUnmatchedFiles ? 'Hide' : 'Show' }} Unmatched Files
            </BaseButton>
          </div>

          <div class="import-pdf-upload__stats">
            <div class="import-pdf-upload__stat import-pdf-upload__stat--success">
              <BaseIcon icon-name="check" class="import-pdf-upload__stat-icon" />
              <div class="import-pdf-upload__stat-content">
                <span class="import-pdf-upload__stat-value">{{ matchedFiles.length }}</span>
                <span class="import-pdf-upload__stat-label">Matched Files</span>
              </div>
            </div>

            <div class="import-pdf-upload__stat import-pdf-upload__stat--warning">
              <BaseIcon icon-name="unavailable" class="import-pdf-upload__stat-icon" />
              <div class="import-pdf-upload__stat-content">
                <span class="import-pdf-upload__stat-value">{{ unmatchedFiles.length }}</span>
                <span class="import-pdf-upload__stat-label">Unmatched Files</span>
              </div>
            </div>

            <div class="import-pdf-upload__stat">
              <BaseIcon icon-name="document" class="import-pdf-upload__stat-icon" />
              <div class="import-pdf-upload__stat-content">
                <span class="import-pdf-upload__stat-value">{{ totalFiles }}</span>
                <span class="import-pdf-upload__stat-label">Total Files</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- File Matching Preview -->
      <div v-if="hasFiles && !isProcessing" class="import-pdf-upload__preview">
        <h4 class="import-pdf-upload__preview-title">File Matching Preview</h4>

        <!-- Matched Files Table -->
        <div v-if="matchedFiles.length > 0" class="import-pdf-upload__matched-section">
          <h5 class="import-pdf-upload__section-title">
            <BaseIcon icon-name="check" class="import-pdf-upload__section-icon" />
            Matched Files ({{ matchedFiles.length }})
          </h5>

          <div class="import-pdf-upload__table-container">
            <table class="import-pdf-upload__table">
              <thead>
                <tr>
                  <th>PDF File</th>
                  <th>Reference Key</th>
                  <th>Title</th>
                  <th>Authors</th>
                  <th>Match Type</th>
                  <th>File Size</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="match in matchedFiles" :key="match.file.name">
                  <td class="import-pdf-upload__table-cell--filename">
                    <BaseIcon icon-name="document" class="import-pdf-upload__file-icon" />
                    {{ match.file.name }}
                  </td>
                  <td class="import-pdf-upload__table-cell--key">{{ match.bibEntry.reference }}</td>
                  <td class="import-pdf-upload__table-cell--title">{{ match.bibEntry.title || "N/A" }}</td>
                  <td class="import-pdf-upload__table-cell--authors">{{ match.bibEntry.authors || "N/A" }}</td>
                  <td class="import-pdf-upload__table-cell--match">
                    <span
                      class="import-pdf-upload__match-badge"
                      :class="`import-pdf-upload__match-badge--${match.matchType}`"
                    >
                      {{ getMatchTypeLabel(match.matchType) }}
                    </span>
                  </td>
                  <td class="import-pdf-upload__table-cell--size">{{ formatFileSize(match.file.size) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Unmatched Files Section -->
        <div v-if="unmatchedFiles.length > 0 && showUnmatchedFiles" class="import-pdf-upload__unmatched-section">
          <h5 class="import-pdf-upload__section-title">
            <BaseIcon icon-name="unavailable" class="import-pdf-upload__section-icon" />
            Unmatched Files ({{ unmatchedFiles.length }})
          </h5>

          <div class="import-pdf-upload__unmatched-list">
            <div
              v-for="file in unmatchedFiles"
              :key="file.name"
              class="import-pdf-upload__unmatched-item"
            >
              <BaseIcon icon-name="document" class="import-pdf-upload__file-icon" />
              <div class="import-pdf-upload__unmatched-info">
                <span class="import-pdf-upload__unmatched-name">{{ file.name }}</span>
                <span class="import-pdf-upload__unmatched-size">{{ formatFileSize(file.size) }}</span>
              </div>
            </div>
          </div>

          <div class="import-pdf-upload__unmatched-help">
            <BaseIcon icon-name="info" class="import-pdf-upload__help-icon" />
            <p>
              These files couldn't be automatically matched to bibliography entries.
              They will be skipped during import unless manually associated.
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import "assets/icons/check";
import "assets/icons/danger";
import "assets/icons/document";
import "assets/icons/import";
import "assets/icons/info";
import "assets/icons/unavailable";

export default {
  name: "ImportPdfUpload",

  props: {
    bibEntries: {
      type: Array,
      default: () => [],
    },
  },

  data() {
    return {
      isDragOver: false,
      isProcessing: false,
      hasError: false,
      errorMessage: "",
      fileErrors: [],
      uploadedFiles: [],
      matchedFiles: [],
      unmatchedFiles: [],
      processedFiles: 0,
      totalFiles: 0,
      showUnmatchedFiles: false,
    };
  },

  computed: {
    hasFiles() {
      return this.uploadedFiles.length > 0;
    },

    getDropzoneIcon() {
      if (this.hasError) return "danger";
      if (this.hasFiles) return "check";
      return "import";
    },

    getDropzoneText() {
      if (this.hasError) return "Error processing files";
      if (this.hasFiles) return `${this.totalFiles} files uploaded`;
      return "Drop PDF files here or click to browse";
    },

    progressPercentage() {
      if (this.totalFiles === 0) return 0;
      return Math.round((this.processedFiles / this.totalFiles) * 100);
    },

    isValid() {
      return this.hasFiles && !this.hasError && this.matchedFiles.length > 0;
    },
  },

  watch: {
    bibEntries: {
      handler() {
        if (this.hasFiles) {
          this.performFileMatching();
        }
      },
      immediate: true,
    },
  },

  methods: {
    selectMultipleFiles() {
      this.$refs.multiFileInput.click();
    },

    selectFolder() {
      this.$refs.fileInput.click();
    },

    triggerFileInput() {
      // Default to multiple file selection
      this.selectMultipleFiles();
    },

    handleDragOver(event) {
      event.preventDefault();
      this.isDragOver = true;
    },

    handleDragLeave() {
      this.isDragOver = false;
    },

    handleDrop(event) {
      event.preventDefault();
      this.isDragOver = false;

      const files = Array.from(event.dataTransfer.files);
      this.processFiles(files);
    },

    handleFileSelect(event) {
      const files = Array.from(event.target.files);
      this.processFiles(files);
    },

    async processFiles(files) {
      // Reset state
      this.hasError = false;
      this.errorMessage = "";
      this.fileErrors = [];
      this.uploadedFiles = [];
      this.matchedFiles = [];
      this.unmatchedFiles = [];
      this.processedFiles = 0;

      // Filter for PDF files only
      const pdfFiles = files.filter(file => this.isValidPdfFile(file));

      if (pdfFiles.length === 0) {
        this.showError("No valid PDF files found. Please upload PDF files only.");
        return;
      }

      if (pdfFiles.length !== files.length) {
        const skippedCount = files.length - pdfFiles.length;
        this.fileErrors.push(`${skippedCount} non-PDF files were skipped`);
      }

      this.totalFiles = pdfFiles.length;
      this.isProcessing = true;

      try {
        // Process files with validation
        for (const file of pdfFiles) {
          await this.processFile(file);
          this.processedFiles++;
        }

        this.uploadedFiles = pdfFiles;

        // Perform file matching with bibliography entries
        this.performFileMatching();

        this.isProcessing = false;
        this.emitUpdate();
      } catch (error) {
        this.isProcessing = false;
        this.showError(`Failed to process files: ${error.message}`);
      }
    },

    async processFile(file) {
      // Validate file size (max 50MB per file)
      const maxSize = 50 * 1024 * 1024; // 50MB
      if (file.size > maxSize) {
        throw new Error(`File ${file.name} is too large (max 50MB)`);
      }

      // Basic PDF validation (check file signature)
      if (!await this.validatePdfFile(file)) {
        throw new Error(`File ${file.name} is not a valid PDF`);
      }

      // Simulate processing delay for UX
      await new Promise(resolve => setTimeout(resolve, 100));
    },

    isValidPdfFile(file) {
      return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
    },

    async validatePdfFile(file) {
      return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = (e) => {
          const arrayBuffer = e.target.result;
          const uint8Array = new Uint8Array(arrayBuffer.slice(0, 4));

          // Check PDF signature (%PDF)
          const pdfSignature = [0x25, 0x50, 0x44, 0x46]; // %PDF
          const isValidPdf = pdfSignature.every((byte, index) => uint8Array[index] === byte);
          resolve(isValidPdf);
        };
        reader.onerror = () => resolve(false);
        reader.readAsArrayBuffer(file.slice(0, 4));
      });
    },

    performFileMatching() {
      if (!this.bibEntries || this.bibEntries.length === 0 || this.uploadedFiles.length === 0) {
        return;
      }

      this.matchedFiles = [];
      this.unmatchedFiles = [];

      for (const file of this.uploadedFiles) {
        const match = this.findBestMatch(file);

        if (match) {
          this.matchedFiles.push({
            file,
            bibEntry: match.entry,
            matchType: match.type,
            confidence: match.confidence,
          });
        } else {
          this.unmatchedFiles.push(file);
        }
      }

      // Sort matched files by confidence (highest first)
      this.matchedFiles.sort((a, b) => b.confidence - a.confidence);
    },

    findBestMatch(file) {
      const fileName = file.name.toLowerCase().replace(/\.pdf$/, "");
      let bestMatch = null;
      let bestConfidence = 0;

      for (const entry of this.bibEntries) {
        const matches = [
          // Exact reference key match
          this.checkExactMatch(fileName, entry.reference),
          // Partial reference key match
          this.checkPartialMatch(fileName, entry.reference),
          // File field match (Zotero exports)
          this.checkFileFieldMatch(fileName, entry.file),
          // Fuzzy title match
          this.checkTitleMatch(fileName, entry.title),
        ].filter(Boolean);

        if (matches.length > 0) {
          const bestFileMatch = matches.reduce((best, current) =>
            current.confidence > best.confidence ? current : best
          );

          if (bestFileMatch.confidence > bestConfidence) {
            bestMatch = {
              entry,
              type: bestFileMatch.type,
              confidence: bestFileMatch.confidence,
            };
            bestConfidence = bestFileMatch.confidence;
          }
        }
      }

      // Only return matches with reasonable confidence
      return bestConfidence >= 0.6 ? bestMatch : null;
    },

    checkExactMatch(fileName, reference) {
      if (!reference) return null;

      const refKey = reference.toLowerCase();
      if (fileName === refKey) {
        return { type: "exact", confidence: 1.0 };
      }
      return null;
    },

    checkPartialMatch(fileName, reference) {
      if (!reference) return null;

      const refKey = reference.toLowerCase();
      if (fileName.includes(refKey) || refKey.includes(fileName)) {
        const similarity = this.calculateStringSimilarity(fileName, refKey);
        if (similarity >= 0.7) {
          return { type: "partial", confidence: similarity };
        }
      }
      return null;
    },

    checkFileFieldMatch(fileName, fileField) {
      if (!fileField) return null;

      // Parse Zotero file field format: "PDF:files/2/filename.pdf:application/pdf"
      const filePaths = fileField.split(";").map(f => f.trim());

      for (const filePath of filePaths) {
        const parts = filePath.split(":");
        if (parts.length >= 2) {
          const path = parts[1].toLowerCase();
          const pathFileName = path.split("/").pop().replace(/\.pdf$/, "");

          if (fileName === pathFileName) {
            return { type: "file_field", confidence: 0.95 };
          }

          const similarity = this.calculateStringSimilarity(fileName, pathFileName);
          if (similarity >= 0.8) {
            return { type: "file_field", confidence: similarity };
          }
        }
      }
      return null;
    },

    checkTitleMatch(fileName, title) {
      if (!title) return null;

      // Clean and normalize title for comparison
      const cleanTitle = title
        .toLowerCase()
        .replace(/[^\w\s]/g, " ")
        .replace(/\s+/g, " ")
        .trim();

      const cleanFileName = fileName
        .replace(/[^\w\s]/g, " ")
        .replace(/\s+/g, " ")
        .trim();

      // Check if filename contains significant words from title
      const titleWords = cleanTitle.split(" ").filter(word => word.length > 3);
      const fileWords = cleanFileName.split(" ");

      let matchedWords = 0;
      for (const titleWord of titleWords) {
        if (fileWords.some(fileWord =>
          fileWord.includes(titleWord) || titleWord.includes(fileWord)
        )) {
          matchedWords++;
        }
      }

      if (titleWords.length > 0) {
        const confidence = matchedWords / titleWords.length;
        if (confidence >= 0.6) {
          return { type: "title", confidence: confidence * 0.8 }; // Lower confidence for title matches
        }
      }

      return null;
    },

    calculateStringSimilarity(str1, str2) {
      // Simple Levenshtein distance-based similarity
      const longer = str1.length > str2.length ? str1 : str2;
      const shorter = str1.length > str2.length ? str2 : str1;

      if (longer.length === 0) return 1.0;

      const distance = this.levenshteinDistance(longer, shorter);
      return (longer.length - distance) / longer.length;
    },

    levenshteinDistance(str1, str2) {
      const matrix = [];

      for (let i = 0; i <= str2.length; i++) {
        matrix[i] = [i];
      }

      for (let j = 0; j <= str1.length; j++) {
        matrix[0][j] = j;
      }

      for (let i = 1; i <= str2.length; i++) {
        for (let j = 1; j <= str1.length; j++) {
          if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
            matrix[i][j] = matrix[i - 1][j - 1];
          } else {
            matrix[i][j] = Math.min(
              matrix[i - 1][j - 1] + 1,
              matrix[i][j - 1] + 1,
              matrix[i - 1][j] + 1
            );
          }
        }
      }

      return matrix[str2.length][str1.length];
    },

    getMatchTypeLabel(matchType) {
      const labels = {
        exact: "Exact",
        partial: "Partial",
        file_field: "File Path",
        title: "Title",
      };
      return labels[matchType] || "Unknown";
    },

    formatFileSize(bytes) {
      if (bytes === 0) return "0 B";

      const k = 1024;
      const sizes = ["B", "KB", "MB", "GB"];
      const i = Math.floor(Math.log(bytes) / Math.log(k));

      return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
    },

    showError(message) {
      this.hasError = true;
      this.errorMessage = message;
      this.emitUpdate();
    },

    emitUpdate() {
      this.$emit("update", {
        isValid: this.isValid,
        matchedFiles: this.matchedFiles,
        unmatchedFiles: this.unmatchedFiles,
        totalFiles: this.totalFiles,
        hasError: this.hasError,
        errorMessage: this.errorMessage,
      });
    },

    // Public methods for parent components
    getUploadData() {
      return {
        matchedFiles: this.matchedFiles,
        unmatchedFiles: this.unmatchedFiles,
        totalFiles: this.totalFiles,
      };
    },

    reset() {
      this.isDragOver = false;
      this.isProcessing = false;
      this.hasError = false;
      this.errorMessage = "";
      this.fileErrors = [];
      this.uploadedFiles = [];
      this.matchedFiles = [];
      this.unmatchedFiles = [];
      this.processedFiles = 0;
      this.totalFiles = 0;
      this.showUnmatchedFiles = false;
      this.emitUpdate();
    },
  },
};
</script>

<style lang="scss" scoped>
.import-pdf-upload {
  padding: $base-space * 3;

  &__header {
    text-align: center;
    margin-bottom: $base-space * 3;
  }

  &__title {
    font-size: 1.25rem;
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
    flex-direction: column;
    gap: $base-space * 3;
  }

  &__file-section {
    display: flex;
    flex-direction: column;
    gap: $base-space * 2;
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
    gap: $base-space * 2;
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
    margin: 0 0 $base-space 0;
    color: var(--fg-primary);
  }

  &__error-list {
    margin: 0;
    padding-left: $base-space * 2;
    color: var(--fg-secondary);
    font-size: 0.9rem;
  }

  &__summary {
    padding: $base-space * 2;
    background: var(--bg-accent-grey-2);
    border-radius: $border-radius;
    border: 1px solid var(--border-field);
  }

  &__summary-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: $base-space * 2;

    h4 {
      margin: 0;
      font-size: 1.1rem;
      color: var(--fg-primary);
    }
  }

  &__stats {
    display: flex;
    gap: $base-space * 3;
    flex-wrap: wrap;
  }

  &__stat {
    display: flex;
    align-items: center;
    gap: $base-space;
    padding: $base-space;
    background: var(--bg-accent-grey-1);
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

    .import-pdf-upload__stat--success & {
      color: var(--color-success);
    }

    .import-pdf-upload__stat--warning & {
      color: var(--color-warning);
    }
  }

  &__stat-content {
    display: flex;
    flex-direction: column;
    gap: $base-space / 4;
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

  &__preview {
    border: 1px solid var(--border-field);
    border-radius: $border-radius-m;
    padding: $base-space * 2;
    background: var(--bg-accent-grey-1);
  }

  &__preview-title {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: $base-space * 2;
    color: var(--fg-primary);
  }

  &__matched-section,
  &__unmatched-section {
    margin-bottom: $base-space * 3;

    &:last-child {
      margin-bottom: 0;
    }
  }

  &__section-title {
    display: flex;
    align-items: center;
    gap: $base-space;
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: $base-space * 2;
    color: var(--fg-primary);
  }

  &__section-icon {
    font-size: 1.1rem;
    color: var(--color-success);

    .import-pdf-upload__unmatched-section & {
      color: var(--color-warning);
    }
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
    &--filename {
      display: flex;
      align-items: center;
      gap: $base-space / 2;
      font-weight: 500;
      max-width: 250px;
    }

    &--key {
      font-family: $quaternary-font-family;
      font-weight: 600;
      color: var(--bg-action);
    }

    &--title {
      font-weight: 500;
      max-width: 300px;
    }

    &--authors {
      max-width: 250px;
    }

    &--match {
      text-align: center;
    }

    &--size {
      text-align: right;
      font-family: $quaternary-font-family;
    }
  }

  &__file-icon {
    color: var(--color-danger);
    font-size: 1rem;
    flex-shrink: 0;
  }

  &__match-badge {
    display: inline-block;
    padding: $base-space / 4 $base-space / 2;
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

  &__unmatched-list {
    display: flex;
    flex-direction: column;
    gap: $base-space;
    margin-bottom: $base-space * 2;
  }

  &__unmatched-item {
    display: flex;
    align-items: center;
    gap: $base-space;
    padding: $base-space;
    background: var(--bg-accent-grey-1);
    border-radius: $border-radius;
    border: 1px solid var(--border-field);
  }

  &__unmatched-info {
    display: flex;
    flex-direction: column;
    gap: $base-space / 4;
    flex: 1;
  }

  &__unmatched-name {
    font-weight: 500;
    color: var(--fg-primary);
  }

  &__unmatched-size {
    font-size: 0.9rem;
    color: var(--fg-secondary);
    font-family: $quaternary-font-family;
  }

  &__unmatched-help {
    display: flex;
    align-items: flex-start;
    gap: $base-space;
    padding: $base-space * 2;
    background: var(--bg-banner-info);
    border: 1px solid var(--bg-action);
    border-radius: $border-radius;
  }

  &__help-icon {
    color: var(--bg-action);
    font-size: 1.1rem;
    margin-top: 0.1rem;
    flex-shrink: 0;
  }

  &__unmatched-help p {
    margin: 0;
    font-size: 0.9rem;
    color: var(--fg-primary);
  }
}
</style>