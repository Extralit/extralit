<template>
  <InternalPage>
    <template #header>
      <AppHeader :breadcrumbs="breadcrumbs" />
    </template>
    <template #page-content>
      <div class="schema-settings">
        <BaseLoading v-if="isLoading" />
        <EmptyState v-else-if="loadFailed" :message="$t('schemas.loadError')" />
        <template v-else-if="settings">
          <h1 class="schema-settings__title">{{ settings.schema.name }} — {{ $t("schemas.settings") }}</h1>

          <section>
            <h2 v-text="$t('schemas.columns')" />
            <table class="schema-settings__table">
              <thead>
                <tr>
                  <th v-text="$t('schemas.name')" />
                  <th v-text="$t('schemas.dtype')" />
                  <th v-text="$t('schemas.nullable')" />
                </tr>
              </thead>
              <tbody>
                <tr v-for="column in currentColumns" :key="column.name">
                  <td>{{ column.name }}</td>
                  <td>{{ column.dtype }}</td>
                  <td>{{ column.nullable ? "✓" : "" }}</td>
                </tr>
              </tbody>
            </table>
          </section>

          <section>
            <h2 v-text="$t('schemas.versions')" />
            <ul>
              <li v-for="version in settings.versions" :key="version.id">
                {{ $t("schemas.version") }} {{ version.version }} — {{ version.insertedAt }}
                <template v-if="version.id === settings.schema.currentVersionId">(current)</template>
              </li>
            </ul>
          </section>

          <section>
            <h2 v-text="$t('schemas.questions')" />
            <table class="schema-settings__table">
              <thead>
                <tr>
                  <th v-text="$t('schemas.name')" />
                  <th v-text="$t('schemas.dtype')" />
                  <th v-text="$t('schemas.columns')" />
                  <th v-text="$t('schemas.required')" />
                </tr>
              </thead>
              <tbody>
                <tr v-for="question in settings.questions" :key="question.id">
                  <td>{{ question.name }}</td>
                  <td>{{ question.type }}</td>
                  <td>{{ question.columns.join(", ") }}</td>
                  <td>{{ question.required ? "✓" : "" }}</td>
                </tr>
              </tbody>
            </table>
          </section>

          <section>
            <BaseButton class="primary" :disabled="isRebuilding" @on-click="rebuildIndex">
              {{ $t("schemas.rebuildIndex") }}
            </BaseButton>
            <p class="schema-settings__hint" v-text="$t('schemas.rebuildIndexHint')" />
          </section>
        </template>
      </div>
    </template>
  </InternalPage>
</template>

<script lang="ts">
import { computed, onBeforeMount } from "vue";
import { useRoute } from "vue-router";
import InternalPage from "@/layouts/InternalPage.vue";
import { useSchemaSettingsViewModel } from "./useSchemaSettingsViewModel";
import { useEnsureWorkspaces } from "~/composables/useEnsureWorkspaces";
import { useV2Breadcrumbs } from "~/composables/useV2Breadcrumbs";

export default {
  components: { InternalPage },
  setup() {
    const route = useRoute();
    const viewModel = useSchemaSettingsViewModel(String(route.params.id));

    const currentColumns = computed(() => {
      const current = viewModel.settings.value?.versions.find(
        (v) => v.id === viewModel.settings.value?.schema.currentVersionId
      );
      return current?.columnsCache ?? [];
    });

    const { ensureWorkspaces } = useEnsureWorkspaces();
    const { schemasBreadcrumbs } = useV2Breadcrumbs();
    const breadcrumbs = computed(() =>
      schemasBreadcrumbs(
        viewModel.settings.value
          ? [
              { name: viewModel.settings.value.schema.name, link: `/schemas/${viewModel.settings.value.schema.id}` },
              { name: "Settings" },
            ]
          : []
      )
    );
    onBeforeMount(ensureWorkspaces);

    return { ...viewModel, currentColumns, breadcrumbs };
  },
};
</script>

<style lang="scss" scoped>
.schema-settings {
  padding: $base-space * 3 0;

  &__title {
    margin: 0 0 $base-space * 2;
    @include font-size(24px);
  }

  section {
    margin-bottom: $base-space * 3;
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

  &__hint {
    color: var(--fg-tertiary);
    font-size: 0.85em;
  }
}
</style>
