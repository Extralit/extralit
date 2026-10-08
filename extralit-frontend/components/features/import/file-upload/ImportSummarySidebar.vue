<template>
  <div class="import-summary-sidebar" :style="{ visibility: hasData ? 'visible' : 'hidden' }">
    <h4 class="import-summary-sidebar__title">Summary status:</h4>

    <div class="import-summary-sidebar__stats">
      <!-- Bibliography Status -->
      <div v-if="bibData.dataframeData && bibData.dataframeData.data.length > 0" class="import-summary-sidebar__stat">
        <BaseIcon
          icon-name="document"
          class="import-summary-sidebar__stat-icon import-summary-sidebar__stat-icon--bib"
        />
        <span class="import-summary-sidebar__stat-text">{{ bibData.dataframeData.data.length }} references found</span>
      </div>

      <!-- PDF Status -->
      <div v-if="pdfData.totalFiles > 0" class="import-summary-sidebar__stat">
        <BaseIcon icon-name="import" class="import-summary-sidebar__stat-icon import-summary-sidebar__stat-icon--pdf" />
        <span class="import-summary-sidebar__stat-text">{{ pdfData.totalFiles }} PDF files uploaded</span>
      </div>

      <!-- Matching Status -->
      <div v-if="pdfData.matchedFiles.length > 0" class="import-summary-sidebar__stat">
        <span class="import-summary-sidebar__stat-text">
          {{ pdfData.matchedFiles.length }} matched, {{ pdfData.unmatchedFiles.length }} mismatch{{
            pdfData.unmatchedFiles.length === 1 ? "" : "es"
          }}
          detected
        </span>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
interface BibliographyData {
  fileName: string;
  dataframeData: any;
  rawContent: string;
}

interface PdfData {
  matchedFiles: any[];
  unmatchedFiles: any[];
  totalFiles: number;
}

export default {
  name: "ImportSummarySidebar",

  props: {
    bibData: {
      type: Object as () => BibliographyData,
      default: () => ({
        fileName: "",
        dataframeData: null,
        rawContent: "",
      }),
    },
    pdfData: {
      type: Object as () => PdfData,
      default: () => ({
        matchedFiles: [],
        unmatchedFiles: [],
        totalFiles: 0,
      }),
    },
  },

  computed: {
    hasData(): boolean {
      return (this.bibData.dataframeData && this.bibData.dataframeData.data.length > 0) || this.pdfData.totalFiles > 0;
    },
  },
};
</script>

<style lang="scss" scoped>
.import-summary-sidebar {
  flex: 1;
  background: var(--bg-accent-grey-1);
  border: 1px solid var(--border-field);
  border-radius: $border-radius-m;
  padding: $base-space * 2;
  height: fit-content;
  position: sticky;
  top: $base-space * 2;
}

.import-summary-sidebar__title {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: $base-space * 2;
  color: var(--fg-primary);
}

.import-summary-sidebar__stats {
  display: flex;
  flex-direction: column;
  gap: $base-space * 2;
  margin-bottom: $base-space * 3;
}

.import-summary-sidebar__stat {
  display: flex;
  align-items: flex-start;
  gap: $base-space;
}

.import-summary-sidebar__stat-icon {
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

.import-summary-sidebar__stat-text {
  color: var(--fg-primary);
  font-size: 0.9rem;
  line-height: 1.4;
}
</style>
