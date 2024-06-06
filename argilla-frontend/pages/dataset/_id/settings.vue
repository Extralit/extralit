<template>
  <BaseLoading v-if="isLoadingDataset" />
  <InternalPage v-else>
    <template v-slot:header>
      <HeaderFeedbackTaskComponent
        :datasetId="datasetId"
        :breadcrumbs="breadcrumbs"
        :showTrainButton="true" 
        @on-click-train="showTrainModal(true)"
      />
      <BaseModal :modal-custom="true" :prevent-body-scroll="true" modal-class="modal-auto"
        modal-position="modal-top-center" :modal-visible="visibleTrainModal" allow-close
        @close-modal="showTrainModal(false)">
        <DatasetTrainComponent datasetTask="FeedbackTask" :datasetName="datasetSetting.dataset.name"
          :workspaceName="datasetSetting.dataset.workspace" />
      </BaseModal>
    </template>
    <template v-slot:page-header>
      <TopDatasetSettingsFeedbackTaskContent
        :separator="!isAdminOrOwnerRole"
        @goToDataset="goToDataset"
      />
    </template>
    <template v-slot:page-content>
      <SettingsInfoReadOnly
        v-if="!isAdminOrOwnerRole"
        :settings="datasetSetting"
      />
      <BaseTabsAndContent
        v-else
        :tabs="tabs"
        tab-size="large"
        class="settings__tabs-content"
      >
        <template v-slot="{ currentComponent }">
          <component
            :is="currentComponent"
            :key="currentComponent"
            :settings="datasetSetting"
          />
        </template>
      </BaseTabsAndContent>
    </template>
  </InternalPage>
</template>

<script>
import InternalPage from "@/layouts/InternalPage";
import { useDatasetSettingViewModel } from "./useDatasetSettingViewModel";

export default {
  name: "SettingPage",
  components: {
    InternalPage,
  },
  data() {
    return {
      visibleTrainModal: false,
    };
  },
  setup() {
    return useDatasetSettingViewModel();
  },
  methods: {
    showTrainModal(value) {
      this.visibleTrainModal = value;
    },
  },
};
</script>

<styles lang="scss" scoped>
.settings {
  &__tabs {
    &-content {
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
</styles>
