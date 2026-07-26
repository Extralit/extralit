<template>
  <InternalPage>
    <template #header>
      <AppHeader :breadcrumbs="breadcrumbs" />
    </template>
    <template #page-content>
      <div class="extractions-page">
        <h1 class="extractions-page__title" v-text="$t('extractions.title')" />

        <EmptyState v-if="!workspaceId" :message="$t('extractions.noWorkspace')" />
        <EmptyState v-else-if="loadFailed" :message="$t('extractions.loadError')" />
        <BaseLoading v-else-if="isLoading || !hasLoaded" />
        <EmptyState v-else-if="!projection || !projection.rows.length" :message="$t('extractions.empty')" />

        <ExtractionsGrid v-else :projection="projection" @cell-click="onCellClick" @load-error="onGridLoadError" />
      </div>
    </template>
  </InternalPage>
</template>

<script lang="ts">
import { computed, onBeforeMount } from "vue";
import { useRoute } from "vue-router";
import InternalPage from "@/layouts/InternalPage.vue";
import { useExtractionsViewModel } from "./useExtractionsViewModel";
import { useEnsureWorkspaces } from "~/composables/useEnsureWorkspaces";
import { useV2Breadcrumbs } from "~/composables/useV2Breadcrumbs";

export default {
  components: { InternalPage },
  setup() {
    const route = useRoute();
    // `?workspace_id=` overrides the selected workspace (deep-load/e2e determinism — the
    // known workspace-hydration gap). Only a single string value is honored; a repeated
    // query param yields an array, which is treated the same as "no override".
    const workspaceIdOverride = typeof route.query.workspace_id === "string" ? route.query.workspace_id : null;

    const viewModel = useExtractionsViewModel(workspaceIdOverride);
    const { ensureWorkspaces } = useEnsureWorkspaces();
    const { extractionsBreadcrumbs } = useV2Breadcrumbs();
    const breadcrumbs = computed(() => extractionsBreadcrumbs());

    onBeforeMount(async () => {
      await ensureWorkspaces();
      await viewModel.load();
    });

    return { ...viewModel, breadcrumbs };
  },
};
</script>

<style lang="scss" scoped>
.extractions-page {
  padding: $base-space * 3 0;

  &__title {
    margin: 0 0 $base-space * 2;
    @include font-size(24px);
  }
}
</style>
