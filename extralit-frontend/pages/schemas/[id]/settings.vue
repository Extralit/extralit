<template>
  <div class="schema-settings">
    <BaseLoading v-if="isLoading" />
    <p v-else-if="loadFailed" class="schema-settings__error" v-text="$t('schemas.loadError')" />
    <template v-else-if="settings">
      <h1>{{ settings.schema.name }} — {{ $t("schemas.settings") }}</h1>

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

<script lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { useSchemaSettingsViewModel } from "./useSchemaSettingsViewModel";

export default {
  setup() {
    const route = useRoute();
    const viewModel = useSchemaSettingsViewModel(String(route.params.id));

    const currentColumns = computed(() => {
      const current = viewModel.settings.value?.versions.find(
        (v) => v.id === viewModel.settings.value?.schema.currentVersionId
      );
      return current?.columnsCache ?? [];
    });

    return { ...viewModel, currentColumns };
  },
};
</script>

<style lang="scss" scoped>
.schema-settings {
  padding: $base-space * 3;

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

  &__error {
    color: var(--fg-tertiary);
  }
}
</style>
