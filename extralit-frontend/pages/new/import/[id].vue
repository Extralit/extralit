<template>
  <div class="new-dataset">
    <HeaderFeedbackTask :breadcrumbs="breadcrumbs" @breadcrumb-action="handleBreadcrumbAction">
      <template #badge>
        <p class="new-dataset__header-badge">
          {{ $t("datasetCreation.preview") }}
        </p>
      </template>
    </HeaderFeedbackTask>

    <div v-if="isLoading" class="loading-container">
      <BaseSpinner />
      <p class="loading-text">{{ $t("importConfiguration.loading") }}</p>
    </div>

    <div v-else-if="error" class="error-container">
      <BaseIcon icon-name="danger" />
      <h3 class="error-title">{{ $t("importConfiguration.errorTitle") }}</h3>
      <p class="error-message">{{ error }}</p>
      <div v-if="retryCount < maxRetries" class="retry-info">
        <p class="retry-text">
          {{ $t("importConfiguration.retryAttempt", { current: retryCount, max: maxRetries }) }}
        </p>
      </div>
      <div class="error-actions">
        <BaseButton variant="primary" :disabled="retryCount >= maxRetries || isLoading" @click="retry">
          {{ isLoading ? $t("importConfiguration.retrying") : $t("importConfiguration.retry") }}
        </BaseButton>
        <BaseButton variant="outline" @click="navigateToHome">
          {{ $t("importConfiguration.returnHome") }}
        </BaseButton>
      </div>
    </div>

    <DatasetConfiguration
      v-else-if="datasetConfig"
      :dataset="datasetConfig"
      data-source="import"
      :import-data="importHistoryData as ImportHistoryDetails"
      @change-subset="handleSubsetChange"
    />
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware(to) {
    if (!to.params.id) {
      return navigateTo("/");
    }
  },
});
</script>

<script lang="ts">
import { type ImportHistoryDetails } from "~/v1/domain/entities/import/ImportHistoryDetails";
import { useImportConfigurationViewModel } from "./useImportConfigurationViewModel";

export default {
  async mounted() {
    const importId = this.getImportId();
    if (importId) {
      await this.loadImportConfiguration(importId);
    } else {
      this.error = "No import ID provided in the URL.";
    }
  },
  setup() {
    return useImportConfigurationViewModel();
  },
  computed: {
    breadcrumbs() {
      const breadcrumbs = [
        {
          link: "/",
          name: this.$t("breadcrumbs.home"),
        },
      ];

      if (this.importHistoryData?.filename) {
        breadcrumbs.push({
          link: "",
          name: `${this.$t("importConfiguration.title")}: ${this.importHistoryData.filename}`,
        });
      } else {
        breadcrumbs.push({
          link: "",
          name: this.$t("importConfiguration.title"),
        });
      }

      return breadcrumbs;
    },
  },
};
</script>

<style scoped lang="scss">
.new-dataset {
  height: 100vh;
  display: flex;
  flex-direction: column;

  &__header-badge {
    background-color: hsl(from var(--color-brand-secondary) h s l);
    color: var(--color-dark-grey);
    padding: calc($base-space / 2) $base-space;
    border-radius: $border-radius;
    margin: 0;
    font-weight: 500;
    margin-left: $base-space * 2;
    @include font-size(12px);
    @include line-height(16px);
  }

  .loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    flex: 1;
    gap: $base-space * 2;

    .loading-text {
      color: var(--fg-secondary);
      margin: 0;
      @include font-size(16px);
    }
  }

  .error-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    flex: 1;
    gap: $base-space * 2;
    padding: $base-space * 4;
    text-align: center;

    .error-title {
      color: var(--fg-primary);
      margin: 0;
      @include font-size(24px);
      font-weight: 600;
    }

    .error-message {
      color: var(--fg-secondary);
      margin: 0;
      @include font-size(16px);
      max-width: 500px;
    }

    .error-actions {
      display: flex;
      gap: $base-space * 2;
      margin-top: $base-space;
    }
  }
}
</style>
