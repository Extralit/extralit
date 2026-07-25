<template>
  <div>
    <Home>
      <template #header>
        <AppHeader
          class="home__header"
          :breadcrumbs="breadcrumbs.map((b) => ({ ...b, name: b.name === 'Home' ? $t('breadcrumbs.home') : b.name }))"
          @breadcrumb-action="onBreadcrumbAction"
        />
        <PersistentStorageBanner class="home__banner" />
      </template>
      <template #page-content>
        <div class="home__tabs">
          <BaseTabs :active-tab="activeTab" :tabs="tabs" tab-size="medium" @change-tab="onTabChange" />
        </div>

        <div class="home__tab-content">
          <template v-if="activeTab.id === 'datasets'">
            <BaseLoading v-if="isLoadingDatasets" />
            <DatasetList
              :workspaces="workspaces"
              :datasets="datasets.datasets"
              :selected-workspace="selectedWorkspace"
              @on-click-card="cardAction"
            />
          </template>

          <template v-if="activeTab.id === 'documents'">
            <div v-if="!selectedWorkspace" class="home__no-workspace">
              <p>Please select a workspace to view documents.</p>
            </div>
            <DocumentsList v-else :key="selectedWorkspace.id" :workspace-id="selectedWorkspace.id" />
          </template>
        </div>
      </template>
      <template #page-sidebar>
        <template v-if="true || isAdminOrOwnerRole">
          <div class="home__sidebar__buttons">
            <ImportDocuments @on-click="openImportFlow" />
            <ImportFromHub
              :is-expanded="showImportDatasetInput"
              :error="error"
              @on-expand="showImportDatasetInput = true"
              @on-close="showImportDatasetInput = false"
              @on-import-dataset="importHfDataset"
            />
          </div>
          <BaseSeparator class="home__sidebar__separator" />
          <div class="home__sidebar__content">
            <RecentImports
              ref="recentImportsComponent"
              :workspace="selectedWorkspace"
              @import-selected="handleImportSelected"
              @view-all-imports="openImportHistoryModal"
              @import-documents="openImportFlow"
            />
          </div>
        </template>
        <template v-else>
          <div class="home__sidebar__content">
            <p class="home__sidebar__title" v-text="$t('home.guidesTitle')" />
            <p class="home__sidebar__subtitle" v-text="$t('home.guidesText')" />
            <div class="home__sidebar__cards">
              <LinkCard
                type="How to guide"
                text="Annotate your dataset"
                link="https://docs.extralit.ai/latest/admin_guide/annotate/"
              />
              <LinkCard
                type="How to guide"
                text="Query and filter records"
                link="https://docs.extralit.ai/latest/admin_guide/query/"
              />
            </div>
            <p class="home__sidebar__link" v-html="$t('home.demoLink')" />
          </div>
        </template>
      </template>
    </Home>

    <ImportFlow
      :is-visible="isImportFlowVisible"
      :workspace="selectedWorkspace"
      @close="showImportFlow = false"
      @import-completed="() => handleImportCompleted($refs.recentImportsComponent)"
    />

    <!-- Import History Modal -->
    <BaseModal
      :modal-visible="isImportHistoryModalVisible"
      :modal-title="$t('import.historyTitle')"
      modal-class="modal-auto"
      @close-modal="closeImportHistoryModal"
    >
      <ImportHistoryList
        :workspace="selectedWorkspace"
        @view-details="handleViewImportDetails"
        @close="closeImportHistoryModal"
      />
    </BaseModal>

    <!-- Import History Details Modal -->
    <BaseModal
      :modal-visible="isImportDetailsModalVisible"
      :modal-title="`Import Details - ${selectedImportDetails?.filename || 'Unknown'}`"
      modal-class="modal-large"
      @close-modal="closeImportDetailsModal"
    >
      <ImportHistoryDetailsModal
        v-if="selectedImportDetails"
        :import-id="selectedImportDetails.importId"
        :filename="selectedImportDetails.filename"
        :workspace="selectedImportDetails.workspace"
        @close="closeImportDetailsModal"
        @retry-item="handleRetryItem"
      />
    </BaseModal>
  </div>
</template>

<script lang="ts">
import Home from "@/layouts/Home.vue";
import { useHomeViewModel } from "./useHomeViewModel";
import { Workspace } from "~/v1/domain/entities/workspace/Workspace";

const NAVIGATION_TAB_ROUTES: Record<string, string> = {
  schemas: "/schemas",
  extractions: "/extractions",
};

export default {
  components: {
    Home,
  },

  setup() {
    return useHomeViewModel();
  },
  data() {
    return {
      showImportDatasetInput: false,
      activeTab: { id: "datasets", name: this.$t("home.datasets") },
      tabs: [
        { id: "datasets", name: this.$t("home.datasets") },
        { id: "documents", name: this.$t("home.documents") },
        { id: "schemas", name: this.$t("schemas.title") },
        { id: "extractions", name: this.$t("extractions.title") },
      ],
      // Import details modal state
      isImportDetailsModalVisible: false,
      selectedImportDetails: null,
    };
  },

  watch: {
    workspaces: {
      immediate: true,
      handler(newWorkspaces) {
        // Auto-assign the first workspace if none is selected and workspaces exist
        if (!this.selectedWorkspace && newWorkspaces && newWorkspaces.length > 0) {
          this.setSelectedWorkspace(newWorkspaces[0]);
        }
      },
    },
  },
  methods: {
    onBreadcrumbAction(e) {
      if (e === "clearFilters") {
        (this.$refs.datasetList as { clearFilters?: () => void })?.clearFilters();
      }
    },
    cardAction(action) {
      if (action === "expand-import-dataset") {
        this.openImportFlow();
      }
    },
    importHfDataset(repoId: string) {
      this.getNewHfDatasetByRepoId(repoId);
    },

    onTabChange(tabId) {
      const route = NAVIGATION_TAB_ROUTES[tabId];
      if (route) {
        this.$router.push(route);
        return;
      }
      const selectedTab = this.tabs.find((tab) => tab.id === tabId);
      if (selectedTab) {
        this.activeTab = selectedTab;
      }
    },
    handleImportSelected(importRecord) {
      this.goToImportConfiguration(importRecord.id);
    },
    handleViewImportDetails(importRecord) {
      this.selectedImportDetails = importRecord;
      this.isImportDetailsModalVisible = true;
    },
    closeImportDetailsModal() {
      this.isImportDetailsModalVisible = false;
      this.selectedImportDetails = null;
    },
    handleRetryItem(item) {
      // Handle retry item functionality if needed
      console.log("Retry item:", item);
    },
  },
};
</script>

<style lang="scss" scoped>
.home {
  &__main {
    display: flex;
    flex-direction: column;
    height: 100vh;

    @include media("<desktop") {
      max-height: 100svh;
    }
  }

  &__header {
    min-height: $topbarHeight;
  }

  &__banner {
    width: auto;
  }

  &__table {
    min-height: 0;
    height: 100%;
    overflow: auto;
    padding: 0;
  }

  &__sidebar {
    &__content {
      display: flex;
      flex-direction: column;
      gap: $base-space;
      overflow: auto;
    }

    &__buttons {
      display: flex;
      gap: $base-space;
      flex-wrap: wrap;
    }

    &__title {
      margin: 0;
      font-weight: 500;
    }

    &__subtitle {
      margin: 0 0 $base-space * 3 0;
      font-weight: 300;
    }

    &__cards {
      display: flex;
      flex-direction: column;
      gap: $base-space * 2;
      margin-bottom: $base-space;
    }

    &__link {
      margin-top: $base-space * 4;
      color: var(--fg-secondary);
    }

    &__separator {
      max-width: 75%;
    }
  }

  &__tabs {
    padding: 0 $base-space * 2;
    margin-bottom: $base-space * 2;
  }

  &__tab-content {
    height: 100%;
    overflow: auto;
  }

  &__no-workspace {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 50vh;
    color: var(--fg-tertiary);
    font-size: 16px;
  }
}
</style>
