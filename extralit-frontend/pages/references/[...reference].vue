<template>
  <div class="reference-review-page">
    <h1 class="reference-review-page__title">{{ $t("review.title") }} — {{ reference }}</h1>

    <BaseLoading v-if="isLoading" />
    <p v-else-if="loadFailed" v-text="$t('review.loadError')" />
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

<script lang="ts">
import { onBeforeMount } from "vue";
import { useRoute } from "vue-router";
import { useReferenceReviewViewModel } from "./useReferenceReviewViewModel";

export default {
  setup() {
    const route = useRoute();
    // Catch-all param: DOIs contain slashes, Nuxt yields the segments as an array (spec §3).
    const segments = route.params.reference;
    const reference = Array.isArray(segments) ? segments.join("/") : String(segments ?? "");
    const workspaceId = String(route.query.workspace_id ?? "");

    const viewModel = useReferenceReviewViewModel(reference, workspaceId);
    onBeforeMount(viewModel.load);

    return { ...viewModel, reference };
  },
};
</script>

<style lang="scss" scoped>
.reference-review-page {
  padding: $base-space * 3;

  &__title {
    margin: 0 0 $base-space * 2;
  }
}
</style>
