<template>
  <div class="import-pdf-upload">
    <div class="import-pdf-upload__header">
      <h2 class="import-pdf-upload__title">Upload PDF Files</h2>
      <p class="import-pdf-upload__description">Upload PDF files to match with your bibliography entries</p>
    </div>

    <div class="import-pdf-upload__content">
      <!-- File Upload Section -->
      <div class="import-pdf-upload__file-section">
        <div
          class="import-pdf-upload__dropzone"
          :class="{
            'import-pdf-upload__dropzone--dragover': isDragOver,
            'import-pdf-upload__dropzone--error': hasError,
            'import-pdf-upload__dropzone--success': uploadedFiles.length > 0,
          }"
          @drop="handleDrop"
          @dragover="handleDragOver"
          @dragleave="handleDragLeave"
          @click="triggerFileInput"
        >
          <input ref="fileInput" type="file" accept=".pdf" multiple style="display: none" @change="handleFileSelect" />

          <div class="import-pdf-upload__dropzone-content">
            <BaseIcon :icon-name="getDropzoneIcon" class="import-pdf-upload__dropzone-icon" />
            <p class="import-pdf-upload__dropzone-text">
              {{ getDropzoneText }}
            </p>
            <p class="import-pdf-upload__dropzone-subtext">
              Supported format: PDF files only. Maximum size: 50MB per file.
            </p>
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

        <!-- Upload Summary -->
        <div v-if="uploadedFiles.length > 0" class="import-pdf-upload__summary">
          <div class="import-pdf-upload__summary-stats">
            <div class="import-pdf-upload__stat">
              <span class="import-pdf-upload__stat-label">Total Files:</span>
              <span class="import-pdf-upload__stat-value">{{ uploadedFiles.length }}</span>
            </div>
            <div class="import-pdf-upload__stat">
              <span class="import-pdf-upload__stat-label">Matched:</span>
              <span class="import-pdf-upload__stat-value import-pdf-upload__stat-value--success">
                {{ matchedCount }}
              </span>
            </div>
            <div class="import-pdf-upload__stat">
              <span class="import-pdf-upload__stat-label">Unmatched:</span>
              <span class="import-pdf-upload__stat-value import-pdf-upload__stat-value--warning">
                {{ unmatchedCount }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- File Matching Preview -->
      <div v-if="uploadedFiles.length > 0" class="import-pdf-upload__matching">
        <h3 class="import-pdf-upload__matching-title">File Matching Preview</h3>

        <!-- Matching Strategy Controls -->
        <div class="import-pdf-upload__controls">
          <div class="import-pdf-upload__control-group">
            <label class="import-pdf-upload__control-label">Matching Strategy:</label>
            <select v-model="matchingStrategy" class="import-pdf-upload__select" @change="performMatching">
              <option value="exact">Exact Match</option>
              <option value="partial">Partial Match</option>
              <option value="fuzzy">Fuzzy Match</option>
            </select>
          </div>

          <BaseButton class="secondary small" @click="performMatching"> Re-match Files </BaseButton>
        </div>

        <!-- File Matching Table -->
        <div class="import-pdf-upload__table-container">
          <table class="import-pdf-upload__table">
            <thead>
              <tr>
                <th>PDF File</th>
                <th>File Size</th>
                <th>Matched Reference</th>
                <th>Match Type</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="file in uploadedFiles"
                :key="file.id"
                :class="{
                  'import-pdf-upload__table-row--matched': file.matchedReference,
                  'import-pdf-upload__table-row--unmatched': !file.matchedReference,
                }"
              >
                <td class="import-pdf-upload__table-cell--filename">
                  <div class="import-pdf-upload__file-info">
                    <BaseIcon icon-name="document" class="import-pdf-upload__file-icon" />
                    <span class="import-pdf-upload__filename" :title="file.name">
                      {{ file.name }}
                    </span>
                  </div>
                </td>
                <td class="import-pdf-upload__table-cell--size">
                  {{ formatFileSize(file.size) }}
                </td>
                <td class="import-pdf-upload__table-cell--reference">
                  <div v-if="file.matchedReference" class="import-pdf-upload__matched-ref">
                    <span class="import-pdf-upload__ref-key">{{ file.matchedReference.reference }}</span>
                    <span class="import-pdf-upload__ref-title">{{ file.matchedReference.title || "No title" }}</span>
                  </div>
                  <span v-else class="import-pdf-upload__unmatched">No match found</span>
                </td>
                <td class="import-pdf-upload__table-cell--match-type">
                  <span
                    v-if="file.matchType"
                    class="import-pdf-upload__match-badge"
                    :class="`import-pdf-upload__match-badge--${file.matchType}`"
                  >
                    {{ file.matchType }}
                  </span>
                  <span v-else class="import-pdf-upload__no-match">-</span>
                </td>
                <td class="import-pdf-upload__table-cell--actions">
                  <div class="import-pdf-upload__actions">
                    <!-- Manual Reference Selection -->
                    <select
                      v-model="file.manualReferenceId"
                      class="import-pdf-upload__reference-select"
                      @change="handleManualMatch(file)"
                    >
                      <option value="">Select reference...</option>
                      <option v-for="entry in bibEntries" :key="entry.reference" :value="entry.reference">
                        {{ entry.reference }} - {{ entry.title || "No title" }}
                      </option>
                    </select>

                    <!-- Remove File Button -->
                    <BaseButton class="danger small" @click="removeFile(file.id)">
                      <BaseIcon icon-name="trash-empty" />
                    </BaseButton>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Unmatched Files Warning -->
        <div v-if="unmatchedCount > 0" class="import-pdf-upload__warning">
          <BaseIcon icon-name="danger" class="import-pdf-upload__warning-icon" />
          <div class="import-pdf-upload__warning-content">
            <h4>{{ unmatchedCount }} file(s) could not be automatically matched</h4>
            <p>Please manually select references for unmatched files or they will be skipped during import.</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
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
      hasError: false,
      errorMessage: "",
      fileErrors: [],
      uploadedFiles: [],
      matchingStrategy: "exact",
      fileIdCounter: 0,
    };
  },

  computed: {
    getDropzoneIcon() {
      if (this.hasError) return "danger";
      if (this.uploadedFiles.length > 0) return "check";
      return "import";
    },

    getDropzoneText() {
      if (this.hasError) return "Error uploading files";
      if (this.uploadedFiles.length > 0) {
        return `${this.uploadedFiles.length} file(s) uploaded`;
      }
      return "Drop your PDF files here or click to browse";
    },

    matchedCount() {
      return this.uploadedFiles.filter((file) => file.matchedReference).length;
    },

    unmatchedCount() {
      return this.uploadedFiles.filter((file) => !file.matchedReference).length;
    },
  },

  watch: {
    bibEntries: {
      handler() {
        // Re-perform matching when bibliography entries change
        if (this.uploadedFiles.length > 0) {
          this.performMatching();
        }
      },
      immediate: true,
    },
  },

  methods: {
    triggerFileInput() {
      this.$refs.fileInput.click();
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
      // Reset error state
      this.hasError = false;
      this.errorMessage = "";
      this.fileErrors = [];

      const validFiles = [];
      const errors = [];

      // Validate each file
      for (const file of files) {
        const validation = this.validateFile(file);
        if (validation.isValid) {
          validFiles.push(file);
        } else {
          errors.push(`${file.name}: ${validation.error}`);
        }
      }

      // Show errors if any
      if (errors.length > 0) {
        this.fileErrors = errors;
        this.hasError = true;
        this.errorMessage = `${errors.length} file(s) failed validation`;
      }

      // Process valid files
      if (validFiles.length > 0) {
        await this.addFiles(validFiles);
        this.performMatching();

        // Emit event to parent
        this.$emit("files-uploaded", {
          files: this.uploadedFiles,
          matchedCount: this.matchedCount,
          unmatchedCount: this.unmatchedCount,
        });
      }
    },

    validateFile(file) {
      // Check file type
      if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
        return {
          isValid: false,
          error: "Only PDF files are allowed",
        };
      }

      // Check file size (50MB limit)
      const maxSize = 50 * 1024 * 1024; // 50MB in bytes
      if (file.size > maxSize) {
        return {
          isValid: false,
          error: `File size (${this.formatFileSize(file.size)}) exceeds 50MB limit`,
        };
      }

      // Check for duplicate filenames
      const isDuplicate = this.uploadedFiles.some((existingFile) => existingFile.name === file.name);
      if (isDuplicate) {
        return {
          isValid: false,
          error: "File with this name already uploaded",
        };
      }

      return { isValid: true };
    },

    async addFiles(files) {
      for (const file of files) {
        const fileData = {
          id: ++this.fileIdCounter,
          name: file.name,
          size: file.size,
          file: file,
          matchedReference: null,
          matchType: null,
          matchScore: 0,
          manualReferenceId: "",
        };

        this.uploadedFiles.push(fileData);
      }
    },

    performMatching() {
      if (this.bibEntries.length === 0) {
        // Clear all matches if no bibliography entries
        this.uploadedFiles.forEach((file) => {
          file.matchedReference = null;
          file.matchType = null;
          file.matchScore = 0;
        });
        return;
      }

      this.uploadedFiles.forEach((file) => {
        const match = this.findBestMatch(file, this.bibEntries);
        file.matchedReference = match.reference;
        file.matchType = match.type;
        file.matchScore = match.score;
      });
    },

    findBestMatch(file, bibEntries) {
      const fileName = file.name.toLowerCase();
      const fileNameWithoutExt = fileName.replace(/\.pdf$/, "");

      let bestMatch = {
        reference: null,
        type: null,
        score: 0,
      };

      for (const entry of bibEntries) {
        const referenceKey = entry.reference.toLowerCase();
        let match = null;

        switch (this.matchingStrategy) {
          case "exact":
            match = this.exactMatch(fileNameWithoutExt, referenceKey);
            break;
          case "partial":
            match = this.partialMatch(fileNameWithoutExt, referenceKey);
            break;
          case "fuzzy":
            match = this.fuzzyMatch(fileNameWithoutExt, referenceKey);
            break;
        }

        if (match && match.score > bestMatch.score) {
          bestMatch = {
            reference: entry,
            type: match.type,
            score: match.score,
          };
        }
      }

      // Only return matches above a minimum threshold
      const minThreshold = this.matchingStrategy === "fuzzy" ? 0.6 : 0.8;
      if (bestMatch.score >= minThreshold) {
        return bestMatch;
      }

      return {
        reference: null,
        type: null,
        score: 0,
      };
    },

    exactMatch(fileName, referenceKey) {
      if (fileName === referenceKey) {
        return { type: "exact", score: 1.0 };
      }
      return null;
    },

    partialMatch(fileName, referenceKey) {
      // Check if filename contains reference key
      if (fileName.includes(referenceKey)) {
        return { type: "partial", score: 0.9 };
      }

      // Check if reference key contains filename (for shorter filenames)
      if (referenceKey.includes(fileName) && fileName.length > 3) {
        return { type: "partial", score: 0.85 };
      }

      return null;
    },

    fuzzyMatch(fileName, referenceKey) {
      const similarity = this.calculateStringSimilarity(fileName, referenceKey);

      if (similarity >= 0.6) {
        return { type: "fuzzy", score: similarity };
      }

      return null;
    },

    calculateStringSimilarity(str1, str2) {
      // Levenshtein distance-based similarity
      const longer = str1.length > str2.length ? str1 : str2;
      const shorter = str1.length > str2.length ? str2 : str1;

      if (longer.length === 0) {
        return 1.0;
      }

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
              matrix[i - 1][j - 1] + 1, // substitution
              matrix[i][j - 1] + 1, // insertion
              matrix[i - 1][j] + 1 // deletion
            );
          }
        }
      }

      return matrix[str2.length][str1.length];
    },

    handleManualMatch(file) {
      if (file.manualReferenceId) {
        const selectedReference = this.bibEntries.find((entry) => entry.reference === file.manualReferenceId);

        if (selectedReference) {
          file.matchedReference = selectedReference;
          file.matchType = "manual";
          file.matchScore = 1.0;
        }
      } else {
        file.matchedReference = null;
        file.matchType = null;
        file.matchScore = 0;
      }

      // Emit update to parent
      this.$emit("files-updated", {
        files: this.uploadedFiles,
        matchedCount: this.matchedCount,
        unmatchedCount: this.unmatchedCount,
      });
    },

    removeFile(fileId) {
      const index = this.uploadedFiles.findIndex((file) => file.id === fileId);
      if (index !== -1) {
        this.uploadedFiles.splice(index, 1);

        // Emit update to parent
        this.$emit("files-updated", {
          files: this.uploadedFiles,
          matchedCount: this.matchedCount,
          unmatchedCount: this.unmatchedCount,
        });
      }
    },

    formatFileSize(bytes) {
      if (bytes === 0) return "0 Bytes";

      const k = 1024;
      const sizes = ["Bytes", "KB", "MB", "GB"];
      const i = Math.floor(Math.log(bytes) / Math.log(k));

      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
    },

    // Public methods for parent components
    getMatchedFiles() {
      return this.uploadedFiles.filter((file) => file.matchedReference);
    },

    getUnmatchedFiles() {
      return this.uploadedFiles.filter((file) => !file.matchedReference);
    },

    getAllFiles() {
      return this.uploadedFiles;
    },

    getFileMatchingData() {
      return {
        files: this.uploadedFiles,
        matchedCount: this.matchedCount,
        unmatchedCount: this.unmatchedCount,
        strategy: this.matchingStrategy,
      };
    },

    reset() {
      this.isDragOver = false;
      this.hasError = false;
      this.errorMessage = "";
      this.fileErrors = [];
      this.uploadedFiles = [];
      this.matchingStrategy = "exact";
      this.fileIdCounter = 0;
    },
  },
};
</script>

<style lang="scss" scoped>
.import-pdf-upload {
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem;

  &__header {
    text-align: center;
    margin-bottom: 2rem;
  }

  &__title {
    font-size: 1.5rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
    color: var(--fg-primary);
  }

  &__description {
    color: var(--fg-secondary);
    margin-bottom: 0;
  }

  &__content {
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  &__file-section {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  &__dropzone {
    border: 2px dashed var(--border-color);
    border-radius: 8px;
    padding: 3rem 2rem;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s ease;
    background: var(--bg-secondary);

    &:hover {
      border-color: var(--primary-color);
      background: var(--bg-tertiary);
    }

    &--dragover {
      border-color: var(--primary-color);
      background: var(--bg-tertiary);
      transform: scale(1.02);
    }

    &--error {
      border-color: var(--error-color);
      background: var(--error-bg);
    }

    &--success {
      border-color: var(--success-color);
      background: var(--success-bg);
    }
  }

  &__dropzone-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
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

  &__error {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 1rem;
    background: var(--error-bg);
    border: 1px solid var(--error-color);
    border-radius: 6px;
  }

  &__error-icon {
    color: var(--error-color);
    font-size: 1.2rem;
    margin-top: 0.1rem;
  }

  &__error-content h4 {
    margin: 0 0 0.5rem 0;
    color: var(--error-color);
    font-size: 1rem;
  }

  &__error-content p {
    margin: 0 0 0.5rem 0;
    color: var(--fg-primary);
  }

  &__error-list {
    margin: 0;
    padding-left: 1.5rem;
    color: var(--fg-secondary);
    font-size: 0.9rem;
  }

  &__summary {
    padding: 1rem;
    background: var(--bg-tertiary);
    border-radius: 6px;
    border: 1px solid var(--border-color);
  }

  &__summary-stats {
    display: flex;
    gap: 2rem;
    flex-wrap: wrap;
  }

  &__stat {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  &__stat-label {
    font-size: 0.9rem;
    color: var(--fg-secondary);
    font-weight: 500;
  }

  &__stat-value {
    font-size: 1.1rem;
    color: var(--fg-primary);
    font-weight: 600;

    &--success {
      color: var(--success-color);
    }

    &--warning {
      color: var(--warning-color);
    }
  }

  &__matching {
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 1.5rem;
    background: var(--bg-primary);
  }

  &__matching-title {
    font-size: 1.2rem;
    font-weight: 600;
    margin-bottom: 1rem;
    color: var(--fg-primary);
  }

  &__controls {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
  }

  &__control-group {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  &__control-label {
    font-size: 0.9rem;
    font-weight: 500;
    color: var(--fg-primary);
  }

  &__select {
    padding: 0.5rem;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    background: var(--bg-primary);
    color: var(--fg-primary);
    font-size: 0.9rem;

    &:focus {
      outline: none;
      border-color: var(--primary-color);
    }
  }

  &__table-container {
    overflow-x: auto;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    margin-bottom: 1rem;
  }

  &__table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;

    th {
      background: var(--bg-secondary);
      padding: 0.75rem;
      text-align: left;
      font-weight: 600;
      color: var(--fg-primary);
      border-bottom: 1px solid var(--border-color);
    }

    td {
      padding: 0.75rem;
      border-bottom: 1px solid var(--border-color);
      color: var(--fg-primary);
      vertical-align: top;
    }

    tr:last-child td {
      border-bottom: none;
    }

    tr:hover {
      background: var(--bg-tertiary);
    }
  }

  &__table-row {
    &--matched {
      background: rgba(56, 142, 60, 0.05);
    }

    &--unmatched {
      background: rgba(245, 124, 0, 0.05);
    }
  }

  &__table-cell {
    &--filename {
      max-width: 250px;
    }

    &--size {
      white-space: nowrap;
    }

    &--reference {
      max-width: 300px;
    }

    &--actions {
      min-width: 200px;
    }
  }

  &__file-info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  &__file-icon {
    color: var(--primary-color);
    font-size: 1.1rem;
  }

  &__filename {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-weight: 500;
  }

  &__matched-ref {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  &__ref-key {
    font-family: monospace;
    font-weight: 600;
    color: var(--primary-color);
    font-size: 0.9rem;
  }

  &__ref-title {
    color: var(--fg-secondary);
    font-size: 0.85rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__unmatched {
    color: var(--warning-color);
    font-style: italic;
  }

  &__match-badge {
    display: inline-block;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 500;
    text-transform: uppercase;

    &--exact {
      background: var(--success-bg);
      color: var(--success-color);
    }

    &--partial {
      background: var(--info-bg);
      color: var(--info-color);
    }

    &--fuzzy {
      background: var(--warning-bg);
      color: var(--warning-color);
    }

    &--manual {
      background: var(--primary-bg);
      color: var(--primary-color);
    }
  }

  &__no-match {
    color: var(--fg-tertiary);
  }

  &__actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  &__reference-select {
    flex: 1;
    min-width: 150px;
    padding: 0.4rem;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    background: var(--bg-primary);
    color: var(--fg-primary);
    font-size: 0.85rem;

    &:focus {
      outline: none;
      border-color: var(--primary-color);
    }
  }

  &__warning {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 1rem;
    background: var(--warning-bg);
    border: 1px solid var(--warning-color);
    border-radius: 6px;
  }

  &__warning-icon {
    color: var(--warning-color);
    font-size: 1.2rem;
    margin-top: 0.1rem;
  }

  &__warning-content h4 {
    margin: 0 0 0.5rem 0;
    color: var(--warning-color);
    font-size: 1rem;
  }

  &__warning-content p {
    margin: 0;
    color: var(--fg-primary);
  }
}

// CSS variables (these would typically be defined in your theme)
:root {
  --fg-primary: #1a1a1a;
  --fg-secondary: #666666;
  --fg-tertiary: #999999;
  --bg-primary: #ffffff;
  --bg-secondary: #f8f9fa;
  --bg-tertiary: #f1f3f4;
  --border-color: #e1e5e9;
  --primary-color: #1976d2;
  --primary-bg: #e3f2fd;
  --error-color: #d32f2f;
  --error-bg: #ffebee;
  --success-color: #388e3c;
  --success-bg: #e8f5e8;
  --warning-color: #f57c00;
  --warning-bg: #fff3e0;
  --info-color: #0288d1;
  --info-bg: #e1f5fe;
}
</style>
