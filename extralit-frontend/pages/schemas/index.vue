<template>
  <InternalPage>
    <template #header>
      <AppHeader :breadcrumbs="breadcrumbs" />
    </template>
    <template #page-content>
      <div class="schemas-page">
        <h1 class="schemas-page__title" v-text="$t('schemas.title')" />

        <Empty v-if="!selectedWorkspace" :message="$t('schemas.noWorkspace')" />
        <BaseLoading v-else-if="isLoading" />
        <Empty v-else-if="loadFailed" :message="$t('schemas.loadError')" />
        <Empty v-else-if="!schemas.length" :message="$t('schemas.empty')" />

        <table v-else class="schemas-page__table">
          <thead>
            <tr>
              <th v-text="$t('schemas.name')" />
              <th v-text="$t('schemas.status')" />
              <th v-text="$t('schemas.updatedAt')" />
              <th />
            </tr>
          </thead>
          <tbody>
            <tr v-for="schema in schemas" :key="schema.id">
              <td>
                <NuxtLink class="schemas-page__link" :to="`/schemas/${schema.id}`">{{ schema.name }}</NuxtLink>
              </td>
              <td><StatusBadge :status="schema.status" /></td>
              <td>{{ schema.updatedAt }}</td>
              <td>
                <NuxtLink class="schemas-page__link" :to="`/schemas/${schema.id}/settings`">
                  {{ $t("schemas.settings") }}
                </NuxtLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </InternalPage>
</template>

<script lang="ts">
import { computed, onBeforeMount } from "vue";
import InternalPage from "@/layouts/InternalPage.vue";
import { useSchemasViewModel } from "./useSchemasViewModel";
import { useEnsureWorkspaces } from "~/composables/useEnsureWorkspaces";
import { useV2Breadcrumbs } from "~/composables/useV2Breadcrumbs";

export default {
  components: { InternalPage },
  setup() {
    const viewModel = useSchemasViewModel();
    const { ensureWorkspaces } = useEnsureWorkspaces();
    const { schemasBreadcrumbs } = useV2Breadcrumbs();
    const breadcrumbs = computed(() => schemasBreadcrumbs());

    onBeforeMount(async () => {
      await ensureWorkspaces();
      await viewModel.loadSchemas();
    });

    return { ...viewModel, breadcrumbs };
  },
};
</script>

<style lang="scss" scoped>
.schemas-page {
  padding: $base-space * 3 0;

  &__title {
    margin: 0 0 $base-space * 2;
    @include font-size(24px);
  }

  &__link {
    color: var(--fg-cuaternary);
    text-decoration: none;
    &:hover {
      text-decoration: underline;
    }
  }

  &__table {
    width: 100%;
    border-collapse: collapse;
    th,
    td {
      text-align: left;
      padding: $base-space;
      border-bottom: 1px solid var(--bg-opacity-10);
    }
    th {
      color: var(--fg-tertiary);
      @include font-size(12px);
    }
  }
}
</style>
