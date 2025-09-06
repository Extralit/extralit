<template>
  <div class="pandera-series-config">
    <div class="pandera-series-config__basic">
      <h6 class="pandera-series-config__section-title">
        {{ $t("datasetCreation.seriesConfiguration") }}
      </h6>
      
      <div class="pandera-series-config__row">
        <label class="pandera-series-config__label">
          {{ $t("datasetCreation.dataType") }}
        </label>
        <BaseSelect
          :value="schema.dtype"
          :options="dtypeOptions"
          @input="updateProperty('dtype', $event)"
          @focus="$emit('is-focused', $event)"
          class="pandera-series-config__dtype"
        />
      </div>
      
      <div v-if="schema.name !== undefined" class="pandera-series-config__row">
        <label class="pandera-series-config__label">
          {{ $t("datasetCreation.seriesName") }}
        </label>
        <BaseInput
          :value="schema.name || ''"
          :placeholder="$t('datasetCreation.seriesNamePlaceholder')"
          @input="updateProperty('name', $event || null)"
          @focus="$emit('is-focused', $event)"
          class="pandera-series-config__name"
        />
      </div>
    </div>
    
    <div class="pandera-series-config__validation">
      <h6 class="pandera-series-config__section-title">
        {{ $t("datasetCreation.validationOptions") }}
      </h6>
      
      <BaseCheckbox
        :value="schema.nullable !== false"
        @input="updateProperty('nullable', $event)"
      >
        {{ $t("datasetCreation.nullable") }}
      </BaseCheckbox>
      
      <BaseCheckbox
        :value="schema.unique || false"
        @input="updateProperty('unique', $event)"
      >
        {{ $t("datasetCreation.unique") }}
      </BaseCheckbox>
      
      <BaseCheckbox
        :value="schema.coerce || false"
        @input="updateProperty('coerce', $event)"
      >
        {{ $t("datasetCreation.coerceTypes") }}
      </BaseCheckbox>
    </div>
    
    <div v-if="schema.description !== undefined || schema.title !== undefined" class="pandera-series-config__metadata">
      <h6 class="pandera-series-config__section-title">
        {{ $t("datasetCreation.metadata") }}
      </h6>
      
      <div v-if="schema.title !== undefined" class="pandera-series-config__row">
        <label class="pandera-series-config__label">
          {{ $t("datasetCreation.title") }}
        </label>
        <BaseInput
          :value="schema.title || ''"
          :placeholder="$t('datasetCreation.titlePlaceholder')"
          @input="updateProperty('title', $event || null)"
          @focus="$emit('is-focused', $event)"
        />
      </div>
      
      <div v-if="schema.description !== undefined" class="pandera-series-config__row">
        <label class="pandera-series-config__label">
          {{ $t("datasetCreation.description") }}
        </label>
        <BaseTextarea
          :value="schema.description || ''"
          :placeholder="$t('datasetCreation.descriptionPlaceholder')"
          :rows="3"
          @input="updateProperty('description', $event || null)"
          @focus="$emit('is-focused', $event)"
        />
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from '@nuxtjs/composition-api';
import { PanderaSeriesSchema } from '~/v1/infrastructure/types/PanderaSchema';

export default defineComponent({
  name: 'DatasetConfigurationPanderaSeries',
  props: {
    schema: {
      type: Object,
      required: true,
    },
  },
  setup(props, { emit }) {
    const schema = props.schema as PanderaSeriesSchema;
    const dtypeOptions = [
      { value: 'str', text: 'String' },
      { value: 'int64', text: 'Integer' },
      { value: 'float64', text: 'Float' },
      { value: 'bool', text: 'Boolean' },
      { value: 'datetime64[ns]', text: 'DateTime' },
      { value: 'object', text: 'Object' },
      { value: 'category', text: 'Category' },
    ];

    const updateProperty = (property: string, value: any) => {
      const updatedSchema = {
        ...schema,
        [property]: value,
      };
      
      emit('update', updatedSchema);
    };

    return {
      dtypeOptions,
      updateProperty,
    };
  },
});
</script>

<style lang="scss" scoped>
.pandera-series-config {
  &__section-title {
    margin: 0 0 0.75rem 0;
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--color-text-secondary);
  }

  &__basic, &__validation, &__metadata {
    margin-bottom: 1.5rem;
    
    &:last-child {
      margin-bottom: 0;
    }
  }

  &__row {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 0.75rem;
  }

  &__label {
    min-width: 100px;
    font-size: 0.875rem;
    font-weight: 500;
  }

  &__dtype, &__name {
    flex: 1;
    max-width: 200px;
  }

  &__validation {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }
}
</style>