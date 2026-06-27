<template>
  <div class="csv-column-selection">
    <div class="csv-column-selection__header">
      <h4 class="csv-column-selection__title">Configure CSV Import</h4>
      <p class="csv-column-selection__description">
        Select the columns that contain reference identifiers and file paths for PDF matching.
      </p>
    </div>

    <div class="csv-column-selection__columns">
      <div class="csv-column-selection__column-group">
        <label class="csv-column-selection__column-label">
          Reference Column (Required)
          <select
            v-model="localConfig.referenceColumn"
            class="csv-column-selection__column-select"
            @change="updateConfig"
          >
            <option value="">Select column...</option>
            <option v-for="column in csvData.columns" :key="column" :value="column">
              {{ column }}
            </option>
          </select>
        </label>
        <p class="csv-column-selection__column-help">
          Column containing unique identifiers for each reference (e.g., citation key, ID)
        </p>
      </div>

      <div class="csv-column-selection__column-group">
        <label class="csv-column-selection__column-label">
          Files Column (Optional)
          <select v-model="localConfig.filesColumn" class="csv-column-selection__column-select" @change="updateConfig">
            <option value="">Select column...</option>
            <option v-for="column in csvData.columns" :key="column" :value="column">
              {{ column }}
            </option>
          </select>
        </label>
        <p class="csv-column-selection__column-help">
          Column containing file paths or names for PDF matching (leave empty if not available)
        </p>
      </div>
    </div>

    <div class="csv-column-selection__preview">
      <h5>Data Preview (first 3 rows):</h5>
      <div class="csv-column-selection__preview-table">
        <table class="csv-column-selection__table">
          <thead>
            <tr>
              <th
                v-for="column in csvData.columns"
                :key="column"
                :class="{
                  'csv-column-selection__preview-header--selected':
                    column === localConfig.referenceColumn || column === localConfig.filesColumn,
                }"
              >
                {{ column }}
                <span v-if="column === localConfig.referenceColumn" class="csv-column-selection__preview-badge"
                  >REF</span
                >
                <span v-if="column === localConfig.filesColumn" class="csv-column-selection__preview-badge">FILES</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in csvData.previewRows" :key="index">
              <td
                v-for="column in csvData.columns"
                :key="column"
                :class="{
                  'csv-column-selection__preview-cell--selected':
                    column === localConfig.referenceColumn || column === localConfig.filesColumn,
                }"
              >
                {{ row[column] || "" }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="csv-column-selection__actions">
      <BaseButton variant="primary" :disabled="!localConfig.referenceColumn" @click="$emit('process-csv')">
        Process CSV Data
      </BaseButton>
      <BaseButton variant="secondary" @click="$emit('cancel')"> Cancel </BaseButton>
    </div>
  </div>
</template>

<script lang="ts">
import type { CSVConfig } from "~/v1/domain/services/IFileParsingService";

interface CsvData {
  rawData: any;
  columns: string[];
  previewRows: any[];
}

export default {
  name: "CsvColumnSelection",

  props: {
    csvData: {
      type: Object as () => CsvData,
      required: true,
    },
    csvConfig: {
      type: Object as () => CSVConfig,
      required: true,
    },
  },

  emits: ["config-updated", "process-csv", "cancel"],

  data() {
    return {
      localConfig: {
        referenceColumn: this.csvConfig.referenceColumn || "",
        filesColumn: this.csvConfig.filesColumn || "",
      } as CSVConfig,
    };
  },

  watch: {
    csvConfig: {
      handler(newConfig: CSVConfig) {
        this.localConfig = {
          referenceColumn: newConfig.referenceColumn || "",
          filesColumn: newConfig.filesColumn || "",
        };
      },
      deep: true,
      immediate: true,
    },
  },

  methods: {
    updateConfig(): void {
      this.$emit("config-updated", { ...this.localConfig });
    },
  },
};
</script>

<style lang="scss" scoped>
.csv-column-selection {
  margin-top: $base-space * 2;
  padding: $base-space * 2;
  background: var(--bg-accent-grey-2);
  border: 1px solid var(--border-field);
  border-radius: $border-radius;
}

.csv-column-selection__header {
  margin-bottom: $base-space * 2;
}

.csv-column-selection__title {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: $base-space;
  color: var(--fg-primary);
}

.csv-column-selection__description {
  color: var(--fg-secondary);
  font-size: 0.9rem;
  margin-bottom: 0;
  line-height: 1.4;
}

.csv-column-selection__columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: $base-space * 2;
  margin-bottom: $base-space * 2;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
}

.csv-column-selection__column-group {
  display: flex;
  flex-direction: column;
  gap: calc($base-space / 2);
}

.csv-column-selection__column-label {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--fg-primary);
  display: flex;
  flex-direction: column;
  gap: calc($base-space / 2);
}

.csv-column-selection__column-select {
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

.csv-column-selection__column-help {
  font-size: 0.8rem;
  color: var(--fg-secondary);
  margin: 0;
  line-height: 1.3;
}

.csv-column-selection__preview {
  margin-bottom: $base-space * 2;

  h5 {
    font-size: 0.9rem;
    font-weight: 600;
    margin-bottom: $base-space;
    color: var(--fg-primary);
  }
}

.csv-column-selection__preview-table {
  overflow-x: auto;
  border: 1px solid var(--border-field);
  border-radius: $border-radius-s;
  background: var(--bg-solid-grey-1);
}

.csv-column-selection__table {
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

.csv-column-selection__preview-header--selected {
  background: var(--bg-action-alpha) !important;
  color: var(--bg-action) !important;
  font-weight: 600;
  position: relative;
}

.csv-column-selection__preview-cell--selected {
  background: var(--bg-action-alpha) !important;
  font-weight: 500;
}

.csv-column-selection__preview-badge {
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

.csv-column-selection__actions {
  display: flex;
  gap: $base-space;
  justify-content: flex-end;

  @media (max-width: 768px) {
    flex-direction: column;
  }
}
</style>
