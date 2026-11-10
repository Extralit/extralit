<template>
  <div class="new-dataset">
    <HeaderFeedbackTask :breadcrumbs="[{ link: '/', name: $t('breadcrumbs.home') }, { name: repoIdWithoutOrg }]">
      <template #badge>
        <p class="new-dataset__header-badge">
          {{ $t("datasetCreation.preview") }}
        </p>
      </template>
    </HeaderFeedbackTask>
    <DatasetConfiguration v-if="datasetConfig" :dataset="datasetConfig" @change-subset="changeSubset($event)" />
  </div>
</template>

<script setup>
import { computed, onMounted } from "vue";
import { useNewDatasetViewModel } from "@/pages/useNewDatasetViewModel";

definePageMeta({
  middleware(to) {
    if (to.params.repoId === "datasets") {
      return navigateTo("/");
    }
  },
});

const route = useRoute();
const { datasetConfig, getNewHfDatasetByRepoId, changeSubset } = useNewDatasetViewModel();

const repoIdWithoutOrg = computed(() => datasetConfig.value?.repoId?.split("/")[1]);

onMounted(() => {
  getNewHfDatasetByRepoId(decodeURIComponent(route.params.repoId));
});
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
}
</style>
