<template>
  <div class="import-upload">
    <div class="import-upload__header">
      <h2 class="import-upload__title">Import Documents</h2>
      <p class="import-upload__description">Upload a .bib file to import your reference library into this workspace</p>
    </div>

    <div class="import-upload__content">
      <!-- File Upload Section -->
      <div class="import-upload__file-section">
        <div
          class="import-upload__dropzone"
          :class="{
            'import-upload__dropzone--dragover': isDragOver,
            'import-upload__dropzone--error': hasError,
            'import-upload__dropzone--success': isFileUploaded,
          }"
          @drop="handleDrop"
          @dragover="handleDragOver"
          @dragleave="handleDragLeave"
          @click="triggerFileInput"
        >
          <input ref="fileInput" type="file" accept=".bib,.bibtex" style="display: none" @change="handleFileSelect" />

          <div class="import-upload__dropzone-content">
            <BaseIcon :icon-name="getDropzoneIcon" class="import-upload__dropzone-icon" />
            <p class="import-upload__dropzone-text">
              {{ getDropzoneText }}
            </p>
            <p class="import-upload__dropzone-subtext">
              Supported formats: .bib, .bibtex (Zotero, EndNote, Mendeley exports)
            </p>
          </div>
        </div>

        <!-- Error Display -->
        <div v-if="hasError" class="import-upload__error">
          <BaseIcon icon-name="danger" class="import-upload__error-icon" />
          <div class="import-upload__error-content">
            <h4>Parsing Error</h4>
            <p>{{ errorMessage }}</p>
            <ul v-if="parseErrors.length > 0" class="import-upload__error-list">
              <li v-for="(error, index) in parseErrors" :key="index">
                {{ error }}
              </li>
            </ul>
          </div>
        </div>

        <!-- Success Display -->
        <div v-if="isFileUploaded && !hasError" class="import-upload__success">
          <BaseIcon icon-name="check" class="import-upload__success-icon" />
          <div class="import-upload__success-content">
            <h4>File Parsed Successfully</h4>
            <p>{{ fileName }} - {{ parsedEntries.length }} references found</p>
          </div>
        </div>
      </div>

      <!-- Preview Section -->
      <div v-if="isFileUploaded && !hasError" class="import-upload__preview">
        <h3 class="import-upload__preview-title">Preview</h3>

        <!-- Summary Stats -->
        <div class="import-upload__stats">
          <div class="import-upload__stat">
            <span class="import-upload__stat-label">Total References:</span>
            <span class="import-upload__stat-value">{{ parsedEntries.length }}</span>
          </div>
          <div class="import-upload__stat">
            <span class="import-upload__stat-label">Fields Detected:</span>
            <span class="import-upload__stat-value">{{ detectedFields.join(", ") }}</span>
          </div>
        </div>

        <!-- Data Preview Table -->
        <div class="import-upload__table-container">
          <table class="import-upload__table">
            <thead>
              <tr>
                <th>Reference Key</th>
                <th>Title</th>
                <th>Authors</th>
                <th>Year</th>
                <th>Type</th>
                <th>DOI</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="entry in previewEntries" :key="entry.reference">
                <td class="import-upload__table-cell--key">{{ entry.reference }}</td>
                <td class="import-upload__table-cell--title">{{ entry.title || "N/A" }}</td>
                <td class="import-upload__table-cell--authors">{{ entry.authors || "N/A" }}</td>
                <td class="import-upload__table-cell--year">{{ entry.year || "N/A" }}</td>
                <td class="import-upload__table-cell--type">{{ entry.type || "N/A" }}</td>
                <td class="import-upload__table-cell--doi">{{ entry.doi || "N/A" }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Show More Button -->
        <div v-if="parsedEntries.length > 5" class="import-upload__show-more">
          <BaseButton class="secondary" @click="showAllEntries = !showAllEntries">
            {{ showAllEntries ? "Show Less" : `Show All ${parsedEntries.length} Entries` }}
          </BaseButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import bibtexParse from "bibtex-parse-js";

export default {
  name: "ImportUpload",

  data() {
    return {
      isDragOver: false,
      isFileUploaded: false,
      hasError: false,
      errorMessage: "",
      parseErrors: [],
      fileName: "",
      rawBibTexContent: "",
      parsedEntries: [],
      dataframeData: null,
      showAllEntries: false,
    };
  },

  computed: {
    getDropzoneIcon() {
      if (this.hasError) return "danger";
      if (this.isFileUploaded) return "check";
      return "import";
    },

    getDropzoneText() {
      if (this.hasError) return "Error parsing file";
      if (this.isFileUploaded) return `${this.fileName} uploaded successfully`;
      return "Drop your .bib file here or click to browse";
    },

    detectedFields() {
      if (this.parsedEntries.length === 0) return [];

      const allFields = new Set();
      this.parsedEntries.forEach((entry) => {
        Object.keys(entry).forEach((field) => allFields.add(field));
      });

      return Array.from(allFields).sort();
    },

    previewEntries() {
      return this.showAllEntries ? this.parsedEntries : this.parsedEntries.slice(0, 5);
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

      const files = event.dataTransfer.files;
      if (files.length > 0) {
        this.processFile(files[0]);
      }
    },

    handleFileSelect(event) {
      const files = event.target.files;
      if (files.length > 0) {
        this.processFile(files[0]);
      }
    },

    async processFile(file) {
      // Reset state
      this.hasError = false;
      this.errorMessage = "";
      this.parseErrors = [];
      this.parsedEntries = [];
      this.dataframeData = null;

      // Validate file type
      if (!this.isValidFileType(file)) {
        this.showError("Invalid file type. Please upload a .bib or .bibtex file.");
        return;
      }

      this.fileName = file.name;

      try {
        // Read file content
        const content = await this.readFileContent(file);
        this.rawBibTexContent = content;

        // Parse BibTeX content
        await this.parseBibTexContent(content);

        if (this.parsedEntries.length > 0) {
          this.isFileUploaded = true;
          this.$emit("file-parsed", {
            fileName: this.fileName,
            parsedEntries: this.parsedEntries,
            dataframeData: this.dataframeData,
            rawContent: this.rawBibTexContent,
          });
        } else {
          this.showError("No valid BibTeX entries found in the file.");
        }
      } catch (error) {
        this.showError(`Failed to process file: ${error.message}`);
      }
    },

    isValidFileType(file) {
      const validExtensions = [".bib", ".bibtex"];
      const fileName = file.name.toLowerCase();
      return validExtensions.some((ext) => fileName.endsWith(ext));
    },

    readFileContent(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result);
        reader.onerror = () => reject(new Error("Failed to read file"));
        reader.readAsText(file, "utf-8");
      });
    },

    async parseBibTexContent(content) {
      try {
        // Parse using bibtex-parse-js
        const parsed = bibtexParse.toJSON(content);

        if (!Array.isArray(parsed) || parsed.length === 0) {
          throw new Error("No valid BibTeX entries found");
        }

        // Convert to our internal format and create dataframe
        this.parsedEntries = [];
        const dataframeEntries = [];
        const errors = [];

        parsed.forEach((entry, index) => {
          try {
            const processedEntry = this.processBibTexEntry(entry, index);
            if (processedEntry) {
              this.parsedEntries.push(processedEntry);
              dataframeEntries.push(this.createDataframeEntry(entry));
            }
          } catch (error) {
            errors.push(`Entry ${index + 1}: ${error.message}`);
          }
        });

        // Store any parsing errors but don't fail completely
        if (errors.length > 0) {
          this.parseErrors = errors;
          console.warn("BibTeX parsing errors:", errors);
        }

        // Create generic dataframe format
        this.dataframeData = this.createGenericDataframe(dataframeEntries);
      } catch (error) {
        throw new Error(`BibTeX parsing failed: ${error.message}`);
      }
    },

    processBibTexEntry(entry, index) {
      // Validate required fields
      if (!entry.citationKey) {
        throw new Error("Missing citation key (reference)");
      }

      // Extract and clean fields
      const processedEntry = {
        reference: entry.citationKey,
        type: entry.entryType || "unknown",
        title: this.cleanBibTexField(entry.entryTags?.title),
        authors: this.extractAuthors(entry.entryTags?.author),
        year: this.extractYear(entry.entryTags?.year || entry.entryTags?.date),
        doi: this.cleanBibTexField(entry.entryTags?.doi),
        pmid: this.cleanBibTexField(entry.entryTags?.pmid),
        url: this.cleanBibTexField(entry.entryTags?.url),
        journal: this.cleanBibTexField(entry.entryTags?.journal),
        volume: this.cleanBibTexField(entry.entryTags?.volume),
        pages: this.cleanBibTexField(entry.entryTags?.pages),
        publisher: this.cleanBibTexField(entry.entryTags?.publisher),
        abstract: this.cleanBibTexField(entry.entryTags?.abstract),
        keywords: this.cleanBibTexField(entry.entryTags?.keywords),
        file: this.cleanBibTexField(entry.entryTags?.file),
      };

      return processedEntry;
    },

    createDataframeEntry(entry) {
      // Create a flattened entry preserving all original fields
      const dataframeEntry = {
        reference: entry.citationKey,
        type: entry.entryType || "unknown",
      };

      // Add all entry tags, preserving original field names and values
      if (entry.entryTags) {
        Object.keys(entry.entryTags).forEach((key) => {
          dataframeEntry[key] = this.cleanBibTexField(entry.entryTags[key]);
        });
      }

      return dataframeEntry;
    },

    createGenericDataframe(entries) {
      if (entries.length === 0) {
        return {
          schema: { fields: [], primaryKey: ["reference"] },
          data: [],
        };
      }

      // Detect all unique fields across entries
      const allFields = new Set(["reference", "type"]); // Always include these
      entries.forEach((entry) => {
        Object.keys(entry).forEach((field) => allFields.add(field));
      });

      // Create schema with type inference
      const fields = Array.from(allFields).map((fieldName) => ({
        name: fieldName,
        type: this.inferFieldType(entries, fieldName),
      }));

      return {
        schema: {
          fields,
          primaryKey: ["reference"],
        },
        data: entries,
      };
    },

    inferFieldType(entries, fieldName) {
      // Simple type inference based on field content
      const values = entries.map((entry) => entry[fieldName]).filter((value) => value != null && value !== "");

      if (values.length === 0) return "string";

      // Check if all values are numbers
      if (values.every((value) => !isNaN(value) && !isNaN(parseFloat(value)))) {
        return values.every((value) => Number.isInteger(parseFloat(value))) ? "integer" : "float";
      }

      return "string";
    },

    cleanBibTexField(field) {
      if (!field) return null;

      // Remove BibTeX formatting (braces, quotes)
      let cleaned = field
        .toString()
        .replace(/^\{+|\}+$/g, "") // Remove outer braces
        .replace(/^"+|"+$/g, "") // Remove outer quotes
        .trim();

      return cleaned || null;
    },

    extractAuthors(authorField) {
      if (!authorField) return null;

      const cleaned = this.cleanBibTexField(authorField);
      if (!cleaned) return null;

      // Handle different author separators
      const authors = cleaned
        .split(/\s+and\s+|\s*,\s*(?=[A-Z])/i)
        .map((author) => author.trim())
        .filter((author) => author.length > 0);

      return authors.length > 0 ? authors.join(", ") : null;
    },

    extractYear(yearField) {
      if (!yearField) return null;

      const cleaned = this.cleanBibTexField(yearField);
      if (!cleaned) return null;

      // Extract 4-digit year from various formats
      const yearMatch = cleaned.match(/\b(19|20)\d{2}\b/);
      return yearMatch ? yearMatch[0] : null;
    },

    showError(message) {
      this.hasError = true;
      this.errorMessage = message;
      this.isFileUploaded = false;
    },

    // Public methods for parent components
    getParsedData() {
      return {
        fileName: this.fileName,
        parsedEntries: this.parsedEntries,
        dataframeData: this.dataframeData,
        rawContent: this.rawBibTexContent,
      };
    },

    reset() {
      this.isDragOver = false;
      this.isFileUploaded = false;
      this.hasError = false;
      this.errorMessage = "";
      this.parseErrors = [];
      this.fileName = "";
      this.rawBibTexContent = "";
      this.parsedEntries = [];
      this.dataframeData = null;
      this.showAllEntries = false;
    },
  },
};
</script>

<style lang="scss" scoped>
.import-upload {
  max-width: 800px;
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

  &__success {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 1rem;
    background: var(--success-bg);
    border: 1px solid var(--success-color);
    border-radius: 6px;
  }

  &__success-icon {
    color: var(--success-color);
    font-size: 1.2rem;
  }

  &__success-content h4 {
    margin: 0 0 0.25rem 0;
    color: var(--success-color);
    font-size: 1rem;
  }

  &__success-content p {
    margin: 0;
    color: var(--fg-primary);
  }

  &__preview {
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 1.5rem;
    background: var(--bg-primary);
  }

  &__preview-title {
    font-size: 1.2rem;
    font-weight: 600;
    margin-bottom: 1rem;
    color: var(--fg-primary);
  }

  &__stats {
    display: flex;
    gap: 2rem;
    margin-bottom: 1.5rem;
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
    font-size: 1rem;
    color: var(--fg-primary);
    font-weight: 600;
  }

  &__table-container {
    overflow-x: auto;
    border: 1px solid var(--border-color);
    border-radius: 6px;
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
      max-width: 200px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    tr:last-child td {
      border-bottom: none;
    }

    tr:hover {
      background: var(--bg-tertiary);
    }
  }

  &__table-cell {
    &--key {
      font-family: monospace;
      font-weight: 600;
      color: var(--primary-color);
    }

    &--title {
      font-weight: 500;
      max-width: 300px;
    }

    &--authors {
      max-width: 250px;
    }
  }

  &__show-more {
    margin-top: 1rem;
    text-align: center;
  }
}

// CSS variables (these would typically be defined in your theme)
:root {
  --fg-primary: #1a1a1a;
  --fg-secondary: #666666;
  --bg-primary: #ffffff;
  --bg-secondary: #f8f9fa;
  --bg-tertiary: #f1f3f4;
  --border-color: #e1e5e9;
  --primary-color: #1976d2;
  --error-color: #d32f2f;
  --error-bg: #ffebee;
  --success-color: #388e3c;
  --success-bg: #e8f5e8;
}
</style>
