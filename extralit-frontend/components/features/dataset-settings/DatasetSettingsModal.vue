<template>
  <BaseModal
    v-if="isVisible"
    :modal-visible="isVisible"
    modal-class="modal-auto"
    :modal-title="$t('settings.title')"
    @close-modal="closeModal"
  >
    <div class="dataset-settings-modal">
      <BaseLoading v-if="isLoadingDataset" />
      <div v-else class="dataset-settings-modal__content">
        <div class="dataset-settings-modal__header">
          <BaseButton @click="closeAndGoToDataset" class="secondary text">
            <svgicon name="chevron-left" width="10" height="10" />
            {{ $t("settings.seeYourDataset") }}
          </BaseButton>
        </div>

        <div class="dataset-settings-modal__body">
          <SettingsInfoReadOnly v-if="!isAdminOrOwnerRole" :settings="datasetSetting" />
          <BaseTabsAndContent
            v-else
            :tabs="tabs"
            tab-size="large"
            class="settings__tabs-content"
            @onChanged="onTabChanged"
            @onLoaded="onTabLoaded"
          >
            <template v-slot="{ currentComponent }">
              <component :is="currentComponent" :key="currentComponent" :settings="datasetSetting" />
            </template>
          </BaseTabsAndContent>
        </div>
      </div>
    </div>
  </BaseModal>
</template>

<script>
import { computed, watch, ref } from "vue-demi";
import { useDatasetSettingsModal } from "@/v1/store/datasetSettingsModal";
import { useDatasetSettingModalViewModel } from "./useDatasetSettingModalViewModel";
import { useRoutes } from "@/v1/infrastructure/services/useRoutes";

export default {
  name: "DatasetSettingsModal",
  setup() {
    const modalStore = useDatasetSettingsModal();
    const routes = useRoutes();

    // Create reactive refs for the view model state
    const viewModelState = ref(null);

    // Watch for changes to the datasetId and create/update the view model
    watch(
      () => modalStore.datasetId,
      (datasetId) => {
        if (datasetId) {
          viewModelState.value = useDatasetSettingModalViewModel(datasetId);
        } else {
          viewModelState.value = null;
        }
      },
      { immediate: true }
    );

    const closeModal = () => {
      // Handle unsaved changes warning if needed
      if (viewModelState.value) {
        viewModelState.value.goToOutside(() => {
          modalStore.closeModal();
        });
      } else {
        modalStore.closeModal();
      }
    };

    const closeAndGoToDataset = () => {
      modalStore.closeModal();
      if (modalStore.datasetId) {
        routes.goToFeedbackTaskAnnotationPage(modalStore.datasetId);
      }
    };

    return {
      isVisible: modalStore.isVisible,
      isLoadingDataset: computed(() => viewModelState.value?.isLoadingDataset || false),
      breadcrumbs: computed(() => viewModelState.value?.breadcrumbs || []),
      tabs: computed(() => viewModelState.value?.tabs || []),
      isAdminOrOwnerRole: computed(() => viewModelState.value?.isAdminOrOwnerRole || false),
      datasetSetting: computed(() => viewModelState.value?.datasetSetting || {}),
      onTabChanged: (tabId) => viewModelState.value?.onTabChanged(tabId),
      onTabLoaded: () => viewModelState.value?.onTabLoaded(),
      closeModal,
      closeAndGoToDataset,
    };
  },
};
</script>

<style lang="scss" scoped>
.dataset-settings-modal {
  max-height: 80vh;
  overflow-y: auto;

  &__content {
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  &__header {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    padding-bottom: 1em;
    border-bottom: 1px solid var(--border-light);
    margin-bottom: 1em;
  }

  &__body {
    flex: 1;
    min-height: 0;

    .settings__tabs-content {
      display: flex;
      flex-direction: column;
      height: 100%;
      min-height: 0;

      .tabs {
        flex-wrap: wrap;
      }
    }
  }
}

// Make the modal wider for settings content
:deep(.modal-container) {
  max-width: 800px;
  width: 90vw;
}
</style>
