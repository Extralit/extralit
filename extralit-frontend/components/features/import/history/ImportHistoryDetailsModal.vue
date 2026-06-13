<template>
  <div class="import-history-details-modal">
    <!-- Header -->
    <div class="details-header">
      <div class="header-content">
        <div class="header-info">
          <h3>Import Details</h3>
          <p class="details-subtitle">
            {{ importId ? `Import ID: ${importId}` : 'Unknown Import' }}
          </p>
        </div>
        <div class="header-actions">
          <BaseButton
            variant="outline"
            @click="close"
            class="close-btn"
          >
            <BaseIcon icon-name="close" />
            Close
          </BaseButton>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="loading-container">
      <BaseSpinner />
      <p>Loading import details...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-container">
      <BaseIcon icon-name="danger" class="error-icon" />
      <h4>Failed to Load Import Details</h4>
      <p>{{ error }}</p>
      <BaseButton variant="outline" @click="loadDetails">
        Retry
      </BaseButton>
    </div>

    <!-- Main Content -->
    <div v-else-if="importHistoryDetails" class="details-content">
      <ImportHistoryDataPreview
        :import-history-details="importHistoryDetails"
        :loading="isLoading"
        :error="error"
        @retry="loadDetails"
        @row-selected="handleRowSelected"
        @field-selected="handleFieldSelected"
      />
    </div>

    <!-- Empty State -->
    <div v-else class="empty-container">
      <BaseIcon icon-name="document" class="empty-icon" />
      <h4>No Details Found</h4>
      <p>No detailed information available for this import.</p>
    </div>
  </div>
</template>

<script lang="ts">

import { useResolve } from "ts-injecty";
import { ImportHistoryDetails } from "~/v1/domain/entities/import/ImportHistoryDetails";
import { GetImportHistoryDetailsUseCase } from "~/v1/domain/usecases/get-import-history-details-use-case";
import ImportHistoryDataPreview from "./ImportHistoryDataPreview.vue";

export default {
  name: "ImportHistoryDetailsModal",

  components: {
    ImportHistoryDataPreview,
  },

  props: {
    importId: {
      type: String,
      required: true,
    },
    filename: {
      type: String,
      default: "",
    },
    workspace: {
      type: Object,
      default: null,
    },
  },

  emits: ["close", "retry-item"],

  data() {
    return {
      // Data state
      importHistoryDetails: null as ImportHistoryDetails | null,

      // UI state
      isLoading: false,
      error: null as string | null,
    };
  },

  async mounted() {
    await this.loadDetails();
  },

  methods: {
    async loadDetails() {
      this.isLoading = true;
      this.error = null;

      try {
        // Get the use case from the DI container
        const getImportHistoryDetailsUseCase = useResolve(GetImportHistoryDetailsUseCase);

        // Fetch the import history details
        const result = await getImportHistoryDetailsUseCase.execute(this.importId);

        if (!result) {
          throw new Error("No import details received");
        }

        // Convert raw data to ImportHistoryDetails instance
        this.importHistoryDetails = new ImportHistoryDetails(result);
      } catch (error: any) {
        console.error('Error loading import details:', error);
        this.error = error.message || 'Failed to load import details';
      } finally {
        this.isLoading = false;
      }
    },

    handleRowSelected(rowData: any) {
      // Handle row selection if needed
      console.log('Row selected:', rowData);
    },

    handleFieldSelected(fieldData: any) {
      // Handle field selection if needed
      console.log('Field selected:', fieldData);
    },

    close() {
      this.$emit("close");
    },
  },
};
</script>

<style lang="scss" scoped>
.import-history-details-modal {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: $base-space * 3;
}

// Header
.details-header {
  margin-bottom: $base-space * 3;

  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: start;
    gap: $base-space * 2;

    .header-info {
      flex: 1;

      h3 {
        margin: 0 0 $base-space 0;
        color: var(--fg-primary);
        font-size: 1.5rem;
        font-weight: 600;
      }

      .details-subtitle {
        margin: 0;
        color: var(--fg-secondary);
        font-size: 1rem;
      }
    }

    .header-actions {
      display: flex;
      gap: $base-space;

      .close-btn {
        display: flex;
        align-items: center;
        gap: calc($base-space / 2);
        white-space: nowrap;
      }
    }
  }
}

// Loading state
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  gap: $base-space * 2;

  p {
    margin: 0;
    color: var(--fg-secondary);
    font-size: 1rem;
  }
}

// Error state
.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  gap: $base-space * 2;
  text-align: center;

  .error-icon {
    font-size: 3rem;
    color: var(--color-danger);
  }

  h4 {
    margin: 0;
    color: var(--color-danger);
    font-size: 1.3rem;
    font-weight: 600;
  }

  p {
    margin: 0;
    color: var(--fg-primary);
    font-size: 1rem;
    max-width: 400px;
  }
}

// Empty state
.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  gap: $base-space * 2;
  text-align: center;

  .empty-icon {
    font-size: 3rem;
    color: var(--fg-secondary);
  }

  h4 {
    margin: 0;
    color: var(--fg-primary);
    font-size: 1.3rem;
    font-weight: 600;
  }

  p {
    margin: 0;
    color: var(--fg-secondary);
    font-size: 1rem;
    max-width: 400px;
    line-height: 1.4;
  }
}

// Main content
.details-content {
  flex: 1;
  min-height: 0;
}

// Responsive design
@media (max-width: 768px) {
  .import-history-details-modal {
    padding: $base-space * 2;
  }

  .header-content {
    flex-direction: column;
    align-items: stretch;

    .header-actions {
      justify-content: flex-end;
    }
  }
}
</style>