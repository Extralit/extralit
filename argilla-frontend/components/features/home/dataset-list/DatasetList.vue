<template>
  <div class="dataset-list__wrapper">
    <div class="dataset-list__header">
      <h1 class="dataset-list__title" v-text="$t('home.argillaDatasets')" />
      <div class="dataset-list__filters">
        <WorkspacesFilter
          :workspaces="formattedWorkspaces"
          v-model="selectedWorkspace"
          @on-change-workspace-filter="onChangeWorkspaceFilter"
        />
        <DatasetsSort
          @on-change-direction="onChangeDirection"
          @on-change-field="onChangeField"
          :sorted-by-field="sortedByField"
          :sorted-order="sortedOrder"
          :sort-options="sortOptions"
        />
        <BaseSearchBar @input="onSearch" :querySearch="querySearch" :placeholder="$t('searchDatasets')" />
      </div>
    </div>
    <div class="dataset-list__content">
      <DatasetListCards v-if="datasets.length" :datasets="filteredDatasetsByWorkspaces" />
      <DatasetsEmpty v-else @on-click-card="cardAction" />
    </div>
  </div>
</template>

<script>
export default {
  props: {
    workspaces: {
      type: Array,
      required: true,
    },
    datasets: {
      type: Array,
      required: true,
    },
  },
  data() {
    return {
      querySearch: "",
      sortedOrder: "desc",
      sortedByField: "lastActivityAt",
      sortOptions: [
        { value: "name", label: this.$t("home.name") },
        { value: "lastActivityAt", label: this.$t("home.updatedAt") },
        { value: "createdAt", label: this.$t("home.createdAt") },
      ],
      selectedWorkspace: null,
    };
  },
  computed: {
    filteredDatasets() {
      return this.sortedDatasets.filter((dataset) =>
        dataset.name.toLowerCase().includes(this.querySearch?.toLowerCase())
      );
    },
    filteredDatasetsByWorkspaces() {
      return this.selectedWorkspace
        ? this.filteredDatasets.filter((dataset) => dataset.workspaceName === this.selectedWorkspace)
        : this.filteredDatasets;
    },
    sortedDatasets() {
      const compare = (a, b) => {
        const fieldA = a[this.sortedByField];
        const fieldB = b[this.sortedByField];
        return this.sortedOrder === "asc" ? fieldA.localeCompare(fieldB) : fieldB.localeCompare(fieldA);
      };
      return this.datasets.sort(compare);
    },
    formattedWorkspaces() {
      return this.workspaces.map(({ name }) => ({
        name,
        numberOfDatasets: this.datasets.filter((d) => d.workspaceName === name).length,
      }));
    },
  },
  methods: {
    onSearch(event) {
      this.querySearch = event;
    },
    onChangeDirection(direction) {
      this.sortedOrder = direction;
    },
    onChangeField(field) {
      this.sortedByField = field;
    },
    onChangeWorkspaceFilter(workspace) {
      this.selectedWorkspace = workspace;
      // Emit workspace ID for import modal
      const selectedWorkspaceObj = this.workspaces.find(w => w.name === workspace);
      if (selectedWorkspaceObj) {
        this.$emit('workspace-selected', selectedWorkspaceObj.id);
      } else {
        this.$emit('workspace-selected', null);
      }
    },
    cardAction(action) {
      this.$emit("on-click-card", action);
    },
  },
  mounted() {
    this.currentWorkspace = this.$route.query.workspace;
    if (this.currentWorkspace) {
      this.onChangeWorkspaceFilter(this.currentWorkspace);
    }
  },
};
</script>

<style lang="scss" scoped>
.dataset-list {
  &__header {
    display: flex;
    justify-content: space-between;
    gap: $base-space;
    align-items: center;
    margin-bottom: $base-space * 2;
    padding: 0 $base-space * 2;
  }
  &__title {
    margin: 0;
    @include font-size(20px);
    font-weight: 500;
  }
  &__filters {
    display: flex;
    gap: $base-space;
  }
  &__wrapper {
    display: flex;
    flex-direction: column;
    height: 100%;
  }
  &__content {
    @extend %hide-scrollbar;
    @include media(">tablet") {
      overflow-x: auto;
      height: 100%;
      padding: 0 $base-space * 2;
    }
  }
}
</style>
