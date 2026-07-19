<template>
  <InternalPage>
    <template #header>
      <AppHeader :breadcrumbs="breadcrumbs" />
    </template>
    <template #page-content>
      <div class="reference-review-page">
        <h1 class="reference-review-page__title">{{ $t("review.title") }} — {{ reference }}</h1>
        <BaseLoading v-if="isLoading" />
        <V2Empty v-else-if="loadFailed" :message="$t('review.loadError')" />
        <ProjectionReviewForm
          v-else-if="review"
          :review="review"
          :submit-errors="submitErrors"
          @submit="onSubmit"
          @save-draft="onSaveDraft"
          @discard="onDiscard"
        />
      </div>
    </template>
  </InternalPage>
</template>

<script lang="ts">
import { computed, onBeforeMount } from "vue";
import { useRoute } from "vue-router";
import InternalPage from "@/layouts/InternalPage.vue";
import { useReferenceReviewViewModel } from "./useReferenceReviewViewModel";
import { useEnsureWorkspaces } from "~/composables/useEnsureWorkspaces";
import { useV2Breadcrumbs } from "~/composables/useV2Breadcrumbs";

export default {
  components: { InternalPage },
  setup() {
    const route = useRoute();
    // Catch-all param: DOIs contain slashes, Nuxt yields the segments as an array (spec §3).
    const segments = route.params.reference;
    const reference = Array.isArray(segments) ? segments.join("/") : String(segments ?? "");
    const workspaceId = String(route.query.workspace_id ?? "");

    const viewModel = useReferenceReviewViewModel(reference, workspaceId);
    const { ensureWorkspaces } = useEnsureWorkspaces();
    const { schemasBreadcrumbs } = useV2Breadcrumbs();
    const breadcrumbs = computed(() => schemasBreadcrumbs([{ name: reference }]));

    onBeforeMount(async () => {
      await ensureWorkspaces();
      await viewModel.load();
    });

    return { ...viewModel, reference, breadcrumbs };
  },
};
</script>

<style lang="scss" scoped>
.reference-review-page {
  padding: $base-space * 3 0;
  &__title {
    margin: 0 0 $base-space * 2;
    @include font-size(24px);
  }
}
</style>
