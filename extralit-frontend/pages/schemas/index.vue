<template>
  <div class="schemas-page">
    <h1 class="schemas-page__title" v-text="$t('schemas.title')" />

    <p v-if="!selectedWorkspace" class="schemas-page__empty" v-text="$t('schemas.noWorkspace')" />
    <BaseLoading v-else-if="isLoading" />
    <p v-else-if="loadFailed" class="schemas-page__empty" v-text="$t('schemas.loadError')" />
    <p v-else-if="!schemas.length" class="schemas-page__empty" v-text="$t('schemas.empty')" />

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
            <NuxtLink :to="`/schemas/${schema.id}`">{{ schema.name }}</NuxtLink>
          </td>
          <td>{{ schema.status }}</td>
          <td>{{ schema.updatedAt }}</td>
          <td>
            <NuxtLink :to="`/schemas/${schema.id}/settings`">{{ $t("schemas.settings") }}</NuxtLink>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script lang="ts">
import { useSchemasViewModel } from "./useSchemasViewModel";

export default {
  setup() {
    return useSchemasViewModel();
  },
};
</script>

<style lang="scss" scoped>
.schemas-page {
  padding: $base-space * 3;

  &__title {
    margin: 0 0 $base-space * 2;
  }

  &__empty {
    color: var(--fg-tertiary);
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
  }
}
</style>
