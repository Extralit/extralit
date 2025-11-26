<template>
  <div class="pdf-upload">
    <div class="pdf-upload__section-header">
      <h3 class="pdf-upload__section-title">Step 1: Upload Your PDF Files</h3>
      <p class="pdf-upload__section-description">
        Upload your PDF files.<br />
        If you upload a BibTeX/CSV file later, Extralit will automatically match the PDFs to your references.
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
        <div class="pdf-upload__progress-fill" :style="{ width: `${progressPercentage()}%` }"></div>
      </div>
    </div>

    <!-- Success Display -->
    <div v-if="uploaded && !hasError && !processing" class="pdf-upload__upload-success">
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
import "assets/icons/check";
import "assets/icons/danger";
import "assets/icons/import";
import { usePdfUploadLogic } from "./usePdfUploadLogic";
import type { PdfData } from "./types";

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
      type: Object,
      default: () => null,
    },
  },

  emits: ["update"],

  setup(props: any, { emit }: any) {
    return usePdfUploadLogic(props, emit);
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
