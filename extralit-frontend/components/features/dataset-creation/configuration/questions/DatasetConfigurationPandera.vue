<template>
  <div class="pandera-schema-config">
    <div class="pandera-schema-config__header">
      <h4 class="pandera-schema-config__title">
        {{ $t("datasetCreation.panderaSchemaValidation") }}
      </h4>
      <BaseToggle 
        :value="hasPanderaSchema" 
        @input="togglePanderaSchema"
        class="pandera-schema-config__toggle"
      />
    </div>
    
    <div v-if="hasPanderaSchema" class="pandera-schema-config__content">
      <div class="pandera-schema-config__type-selector">
        <BaseRadioButton
          name="schema-type"
          :value="schemaType"
          value-option="dataframe"
          @input="setSchemaType('dataframe')"
        >
          {{ $t("datasetCreation.dataFrameSchema") }}
        </BaseRadioButton>
        <BaseRadioButton
          name="schema-type"
          :value="schemaType"
          value-option="series"
          @input="setSchemaType('series')"
        >
          {{ $t("datasetCreation.seriesSchema") }}
        </BaseRadioButton>
      </div>

      <div v-if="schemaType === 'dataframe'" class="pandera-schema-config__dataframe">
        <DatasetConfigurationPanderaDataFrame 
          :schema="panderaSchema"
          @update="updatePanderaSchema"
          @is-focused="$emit('is-focused', $event)"
        />
      </div>

      <div v-else-if="schemaType === 'series'" class="pandera-schema-config__series">
        <DatasetConfigurationPanderaSeries 
          :schema="panderaSchema"
          @update="updatePanderaSchema"
          @is-focused="$emit('is-focused', $event)"
        />
      </div>

      <div class="pandera-schema-config__json-editor">
        <h5 class="pandera-schema-config__json-title">
          {{ $t("datasetCreation.schemaJsonEditor") }}
        </h5>
        <BaseTextarea
          :value="panderaSchemaJson"
          :placeholder="$t('datasetCreation.panderaSchemaJsonPlaceholder')"
          :rows="10"
          @input="updatePanderaSchemaFromJson"
          class="pandera-schema-config__json-textarea"
        />
        <div v-if="jsonValidationError" class="pandera-schema-config__error">
          {{ jsonValidationError }}
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, computed, ref } from '@nuxtjs/composition-api';
import { Question } from '~/v1/domain/entities/question/Question';
import { 
  PanderaSchema, 
  createEmptyDataFrameSchema, 
  createEmptySeriesSchema,
  validatePanderaSchema 
} from '~/v1/infrastructure/types/PanderaSchema';

export default defineComponent({
  name: 'DatasetConfigurationPandera',
  props: {
    question: {
      type: Object,
      required: true,
    },
  },
  setup(props, { emit }) {
    const question = props.question as Question;
    const jsonValidationError = ref<string | null>(null);

    const hasPanderaSchema = computed(() => question.hasPanderaSchema);

    const panderaSchema = computed(() => question.panderaSchema);

    const schemaType = computed(() => {
      if (!panderaSchema.value) return 'dataframe';
      return panderaSchema.value.schema_type === 'SeriesSchema' ? 'series' : 'dataframe';
    });

    const panderaSchemaJson = computed(() => {
      return question.panderaSchemaJson || '';
    });

    const togglePanderaSchema = () => {
      if (hasPanderaSchema.value) {
        question.setPanderaSchema(null);
      } else {
        question.setPanderaSchema(createEmptyDataFrameSchema());
      }
    };

    const setSchemaType = (type: 'dataframe' | 'series') => {
      if (type === 'dataframe') {
        question.setPanderaSchema(createEmptyDataFrameSchema());
      } else {
        question.setPanderaSchema(createEmptySeriesSchema());
      }
    };

    const updatePanderaSchema = (schema: PanderaSchema) => {
      question.setPanderaSchema(schema);
    };

    const updatePanderaSchemaFromJson = (jsonString: string) => {
      jsonValidationError.value = null;
      
      if (!jsonString.trim()) {
        question.setPanderaSchema(null);
        return;
      }

      try {
        const schema = JSON.parse(jsonString);
        const validation = validatePanderaSchema(schema);
        
        if (validation.isValid) {
          question.setPanderaSchema(schema);
        } else {
          jsonValidationError.value = validation.errors?.join(', ') || 'Invalid schema format';
        }
      } catch (error) {
        jsonValidationError.value = 'Invalid JSON format';
      }
    };

    return {
      hasPanderaSchema,
      panderaSchema,
      schemaType,
      panderaSchemaJson,
      jsonValidationError,
      togglePanderaSchema,
      setSchemaType,
      updatePanderaSchema,
      updatePanderaSchemaFromJson,
    };
  },
});
</script>

<style lang="scss" scoped>
.pandera-schema-config {
  &__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  &__title {
    margin: 0;
    font-size: 1rem;
    font-weight: 500;
  }

  &__content {
    border: 1px solid var(--color-border);
    border-radius: 4px;
    padding: 1rem;
    background-color: var(--color-background-light);
  }

  &__type-selector {
    display: flex;
    gap: 1rem;
    margin-bottom: 1rem;
  }

  &__json-title {
    margin: 1rem 0 0.5rem 0;
    font-size: 0.875rem;
    font-weight: 500;
  }

  &__json-textarea {
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 0.75rem;
  }

  &__error {
    color: var(--color-error);
    font-size: 0.75rem;
    margin-top: 0.5rem;
  }
}
</style>