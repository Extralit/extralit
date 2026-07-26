<template>
  <InternalPage>
    <template #header>
      <AppHeader :breadcrumbs="breadcrumbs" />
    </template>
    <template #page-content>
      <div class="schema-detail">
        <div class="schema-detail__header">
          <h1 class="schema-detail__title">{{ schema?.name }}</h1>
          <BaseButton v-if="schema" class="secondary small" :to="`/schemas/${schema.id}/settings`">
            {{ $t("schemas.settings") }}
          </BaseButton>
        </div>

        <div class="schema-detail__search">
          <!-- Native input rather than BaseSearchBar: the shared BaseInput debounces its
               update:modelValue emit while re-rendering a controlled :value, which resets the
               DOM value to the stale model on every keystroke — losing characters under fast
               typing and dropping Playwright fill() entirely. v-model on a native input is
               immediate and lossless; search fires on Enter (the spec's fill + press("Enter")). -->
          <input
            v-model="searchText"
            type="search"
            class="schema-detail__search-input"
            :placeholder="$t('schemas.searchPlaceholder')"
            @keyup.enter="onSearch"
          />
          <select v-model="statusFilter" class="schema-detail__status" @change="onSearch">
            <option value="">{{ $t("schemas.status") }}</option>
            <option value="pending">pending</option>
            <option value="completed">completed</option>
            <option value="discarded">discarded</option>
          </select>
        </div>

        <BaseLoading v-if="isLoading" />
        <template v-else>
          <p v-if="page.items.length" class="schema-detail__total">
            <template v-if="isApproximateTotal">{{ $t("schemas.totalApproximate", { total: page.total }) }}</template>
            <template v-else>{{ page.total }}</template>
          </p>
          <V2RecordsTable v-if="page.items.length" :records="page.items" :columns="columns" />
          <V2Empty v-else :message="$t('schemas.noResults')" />

          <!-- Pager stays outside the results branch so advancing onto an empty page (approximate
               totals let "next" run one page too far) still shows a way back instead of a dead-end. -->
          <div v-if="currentOffset > 0 || page.items.length >= pageSize" class="schema-detail__pager">
            <BaseButton
              class="secondary small"
              :disabled="currentOffset === 0"
              @click="goToOffset(currentOffset - pageSize)"
              >‹</BaseButton
            >
            <!-- total is approximate: allow next only while a full page keeps coming back -->
            <BaseButton
              class="secondary small"
              :disabled="page.items.length < pageSize"
              @click="goToOffset(currentOffset + pageSize)"
              >›</BaseButton
            >
          </div>
        </template>
      </div>
    </template>
  </InternalPage>
</template>

<script lang="ts">
import { computed, onBeforeMount } from "vue";
import { useRoute } from "vue-router";
import InternalPage from "@/layouts/InternalPage.vue";
import { useSchemaRecordsViewModel } from "./useSchemaRecordsViewModel";
import { useEnsureWorkspaces } from "~/composables/useEnsureWorkspaces";
import { useV2Breadcrumbs } from "~/composables/useV2Breadcrumbs";

export default {
  components: { InternalPage },
  setup() {
    const route = useRoute();
    const viewModel = useSchemaRecordsViewModel(String(route.params.id));
    const { ensureWorkspaces } = useEnsureWorkspaces();
    const { schemasBreadcrumbs } = useV2Breadcrumbs();

    const breadcrumbs = computed(() =>
      schemasBreadcrumbs(viewModel.schema.value ? [{ name: viewModel.schema.value.name }] : [])
    );

    const onSearch = async () => {
      viewModel.currentOffset.value = 0;
      await viewModel.search();
    };

    onBeforeMount(ensureWorkspaces);

    return { ...viewModel, breadcrumbs, onSearch };
  },
};
</script>

<style lang="scss" scoped>
.schema-detail {
  padding: $base-space * 3 0;
  &__header {
    display: flex;
    align-items: baseline;
    gap: $base-space * 2;
  }
  &__title {
    margin: 0 0 $base-space * 2;
    @include font-size(24px);
  }
  &__search {
    display: flex;
    gap: $base-space;
    margin-bottom: $base-space * 2;
  }
  &__search-input {
    flex: 1;
    padding: $base-space * 1.2 $base-space * 1.5;
    border: 1px solid var(--bg-opacity-10);
    border-radius: $border-radius;
    background: var(--bg-accent-grey-1);
    color: var(--fg-secondary);
    @include font-size(14px);
    &::placeholder {
      color: var(--fg-tertiary);
    }
    &:focus {
      outline: none;
      border-color: var(--fg-cuaternary);
    }
  }
  &__status {
    padding: 0 $base-space;
    border: 1px solid var(--bg-opacity-10);
    border-radius: $border-radius;
    background: transparent;
    color: var(--fg-secondary);
  }
  &__total {
    color: var(--fg-tertiary);
  }
  &__pager {
    display: flex;
    gap: $base-space;
    margin-top: $base-space * 2;
  }
}
</style>
