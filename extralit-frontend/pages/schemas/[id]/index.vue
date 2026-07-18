<template>
  <div class="schema-detail">
    <div class="schema-detail__header">
      <h1 class="schema-detail__title">{{ schema?.name }}</h1>
      <NuxtLink v-if="schema" :to="`/schemas/${schema.id}/settings`">{{ $t("schemas.settings") }}</NuxtLink>
    </div>

    <form class="schema-detail__search" @submit.prevent="onSearch">
      <input
        v-model="searchText"
        class="schema-detail__search-input"
        type="search"
        :placeholder="$t('schemas.searchPlaceholder')"
      />
      <select v-model="statusFilter" @change="onSearch">
        <option value="">{{ $t("schemas.status") }}</option>
        <option value="pending">pending</option>
        <option value="completed">completed</option>
        <option value="discarded">discarded</option>
      </select>
    </form>

    <BaseLoading v-if="isLoading" />
    <template v-else>
      <p v-if="page.items.length" class="schema-detail__total">
        <template v-if="isApproximateTotal">{{ $t("schemas.totalApproximate", { total: page.total }) }}</template>
        <template v-else>{{ page.total }}</template>
      </p>
      <V2RecordsTable
        v-if="page.items.length"
        :records="page.items"
        :columns="columns"
        :workspace-id="schema?.workspaceId ?? ''"
      />
      <p v-else class="schema-detail__empty" v-text="$t('schemas.noResults')" />

      <!-- Pager stays outside the results branch so advancing onto an empty page (approximate
           totals let "next" run one page too far) still shows a way back instead of a dead-end. -->
      <div v-if="currentOffset > 0 || page.items.length >= pageSize" class="schema-detail__pager">
        <button :disabled="currentOffset === 0" @click="goToOffset(currentOffset - pageSize)">‹</button>
        <!-- total is approximate: allow next only while a full page keeps coming back -->
        <button :disabled="page.items.length < pageSize" @click="goToOffset(currentOffset + pageSize)">›</button>
      </div>
    </template>
  </div>
</template>

<script lang="ts">
import { useRoute } from "vue-router";
import { useSchemaRecordsViewModel } from "./useSchemaRecordsViewModel";

export default {
  setup() {
    const route = useRoute();
    const viewModel = useSchemaRecordsViewModel(String(route.params.id));

    const onSearch = async () => {
      viewModel.currentOffset.value = 0;
      await viewModel.search();
    };

    return { ...viewModel, onSearch };
  },
};
</script>

<style lang="scss" scoped>
.schema-detail {
  padding: $base-space * 3;

  &__header {
    display: flex;
    align-items: baseline;
    gap: $base-space * 2;
  }

  &__title {
    margin: 0 0 $base-space * 2;
  }

  &__search {
    display: flex;
    gap: $base-space;
    margin-bottom: $base-space * 2;
  }

  &__search-input {
    flex: 1;
    padding: $base-space;
  }

  &__total,
  &__empty {
    color: var(--fg-tertiary);
  }

  &__pager {
    display: flex;
    gap: $base-space;
    margin-top: $base-space * 2;
  }
}
</style>
