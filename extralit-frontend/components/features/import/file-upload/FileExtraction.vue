<template>
  <div class="file-extraction">
    <div class="file-extraction__section-header">
      <h3 class="file-extraction__section-title">Step 3: Extract Content (Optional)</h3>
      <p class="file-extraction__section-description">
        Extract text and metadata from your uploaded files using Extractous.
        This helps you preview the content before processing.
      </p>
    </div>

    <!-- Extraction Controls -->
    <div class="file-extraction__controls">
      <div class="file-extraction__file-selector">
        <label for="file-select" class="file-extraction__label">Select a file to extract:</label>
        <select
          id="file-select"
          v-model="selectedFile"
          class="file-extraction__select"
          :disabled="!availableFiles.length || extracting"
        >
          <option value="">Choose a file...</option>
          <option v-for="file in availableFiles" :key="file.name" :value="file">
            {{ file.name }} ({{ formatFileSize(file.size) }})
          </option>
        </select>
      </div>

      <button
        class="file-extraction__extract-btn"
        :disabled="!selectedFile || extracting"
        @click="extractFile"
      >
        <span v-if="extracting">Extracting...</span>
        <span v-else>Extract Content</span>
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="extracting" class="file-extraction__loading">
      <div class="file-extraction__loading-content">
        <span class="file-extraction__loading-icon">⚙️</span>
        <p>Extracting content from {{ selectedFile?.name }}...</p>
      </div>
    </div>

    <!-- Error Display -->
    <div v-if="hasError" class="file-extraction__error">
      <span class="file-extraction__error-icon">❌</span>
      <div class="file-extraction__error-content">
        <h4>Extraction Failed</h4>
        <p>{{ errorMessage }}</p>
      </div>
    </div>

    <!-- Extraction Results -->
    <div v-if="extractionResult && !extracting" class="file-extraction__results">
      <div class="file-extraction__results-header">
        <h4>Extraction Results</h4>
        <span class="file-extraction__results-file">{{ extractionResult.original_filename }}</span>
      </div>

      <!-- Metadata Display -->
      <div class="file-extraction__metadata">
        <h5>File Information</h5>
        <div class="file-extraction__metadata-grid">
          <div class="file-extraction__metadata-item">
            <strong>Content Type:</strong> {{ extractionResult.content_type || 'Unknown' }}
          </div>
          <div class="file-extraction__metadata-item">
            <strong>File Size:</strong> {{ formatFileSize(extractionResult.file_size) }}
          </div>
          <div v-if="extractionResult.metadata" class="file-extraction__metadata-item">
            <strong>Detected Format:</strong> {{ getDetectedFormat(extractionResult.metadata) }}
          </div>
        </div>
      </div>

      <!-- Extracted Text Display -->
      <div class="file-extraction__text">
        <h5>Extracted Text</h5>
        <div class="file-extraction__text-preview">
          {{ extractionResult.extracted_text || 'No text content extracted.' }}
        </div>
      </div>

      <!-- Raw Metadata (collapsible) -->
      <details class="file-extraction__metadata-details">
        <summary>View Technical Metadata</summary>
        <pre class="file-extraction__metadata-raw">{{ formatMetadata(extractionResult.metadata) }}</pre>
      </details>
    </div>
  </div>
</template>

<script lang="ts">
import { useFileExtractionViewModel } from "./useFileExtractionViewModel";

export default {
  name: "FileExtraction",

  props: {
    // Available files from previous upload steps
    availableFiles: {
      type: Array as () => File[],
      default: () => [],
    },
  },

  setup(props: any, { emit }: any) {
    return useFileExtractionViewModel(props, { emit });
  },
};
</script>

<style lang="scss" scoped>
.file-extraction {
  margin-top: $base-space * 3;

  &__section-header {
    margin-bottom: $base-space * 2;
  }

  &__section-title {
    font-size: 1.2rem;
    font-weight: 600;
    margin-bottom: $base-space;
    color: var(--fg-primary);
  }

  &__section-description {
    color: var(--fg-secondary);
    font-size: 0.9rem;
    margin-bottom: 0;
    line-height: 1.4;
  }

  &__controls {
    display: flex;
    gap: $base-space * 2;
    align-items: end;
    margin-bottom: $base-space * 2;

    @media (max-width: 768px) {
      flex-direction: column;
      align-items: stretch;
    }
  }

  &__file-selector {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: calc($base-space / 2);
  }

  &__label {
    font-size: 0.9rem;
    font-weight: 500;
    color: var(--fg-primary);
  }

  &__select {
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

    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  }

  &__extract-btn {
    padding: calc($base-space / 2) $base-space * 2;
    background: var(--bg-action);
    color: white;
    border: none;
    border-radius: $border-radius-s;
    font-size: 0.9rem;
    font-weight: 500;
    cursor: pointer;
    transition: $swift-ease-out;

    &:hover:not(:disabled) {
      background: var(--bg-action-hover);
    }

    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  }

  &__loading {
    padding: $base-space * 2;
    background: var(--bg-accent-grey-2);
    border: 1px solid var(--border-field);
    border-radius: $border-radius;
    text-align: center;
  }

  &__loading-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: $base-space;
  }

  &__loading-icon {
    font-size: 2rem;
    animation: spin 2s linear infinite;
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

  &__results {
    border: 1px solid var(--border-field);
    border-radius: $border-radius;
    overflow: hidden;
  }

  &__results-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: $base-space * 2;
    background: var(--bg-accent-grey-2);
    border-bottom: 1px solid var(--border-field);

    h4 {
      margin: 0;
      color: var(--fg-primary);
    }
  }

  &__results-file {
    font-size: 0.9rem;
    color: var(--fg-secondary);
    font-family: $quaternary-font-family;
  }

  &__metadata,
  &__text {
    padding: $base-space * 2;

    h5 {
      margin: 0 0 $base-space 0;
      font-size: 1rem;
      color: var(--fg-primary);
    }
  }

  &__metadata {
    border-bottom: 1px solid var(--border-field);
  }

  &__metadata-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: $base-space;

    @media (max-width: 768px) {
      grid-template-columns: 1fr;
    }
  }

  &__metadata-item {
    font-size: 0.9rem;
    color: var(--fg-primary);

    strong {
      color: var(--fg-primary);
    }
  }

  &__text-preview {
    max-height: 300px;
    overflow-y: auto;
    padding: $base-space;
    background: var(--bg-accent-grey-1);
    border: 1px solid var(--border-field);
    border-radius: $border-radius-s;
    font-size: 0.9rem;
    line-height: 1.4;
    white-space: pre-wrap;
    word-break: break-word;
  }

  &__metadata-details {
    border-top: 1px solid var(--border-field);

    summary {
      padding: $base-space * 2;
      cursor: pointer;
      font-weight: 500;
      color: var(--fg-primary);

      &:hover {
        background: var(--bg-accent-grey-3);
      }
    }
  }

  &__metadata-raw {
    padding: $base-space * 2;
    background: var(--bg-accent-grey-1);
    font-size: 0.8rem;
    line-height: 1.3;
    overflow-x: auto;
    margin: 0;
    color: var(--fg-primary);
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>