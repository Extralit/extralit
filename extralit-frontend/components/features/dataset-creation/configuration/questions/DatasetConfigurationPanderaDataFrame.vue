<template>
  <div class="pandera-dataframe-config">
    <div class="pandera-dataframe-config__columns">
      <h6 class="pandera-dataframe-config__section-title">
        {{ $t("datasetCreation.columns") }}
      </h6>
      
      <div 
        v-for="(column, columnName) in schema.columns" 
        :key="columnName"
        class="pandera-dataframe-config__column"
      >
        <div class="pandera-dataframe-config__column-header">
          <BaseInput
            :value="columnName"
            :placeholder="$t('datasetCreation.columnName')"
            @input="updateColumnName(columnName, $event)"
            @focus="$emit('is-focused', $event)"
            class="pandera-dataframe-config__column-name"
          />
          <BaseButton
            @click="removeColumn(columnName)"
            class="pandera-dataframe-config__remove-column"
            size="small"
          >
            <svgicon name="close" />
          </BaseButton>
        </div>
        
        <div class="pandera-dataframe-config__column-config">
          <BaseSelect
            :value="column.dtype"
            :options="dtypeOptions"
            @input="updateColumnProperty(columnName, 'dtype', $event)"
            @focus="$emit('is-focused', $event)"
            class="pandera-dataframe-config__dtype"
          />
          
          <BaseCheckbox
            :value="column.nullable || false"
            @input="updateColumnProperty(columnName, 'nullable', $event)"
          >
            {{ $t("datasetCreation.nullable") }}
          </BaseCheckbox>
          
          <BaseCheckbox
            :value="column.unique || false"
            @input="updateColumnProperty(columnName, 'unique', $event)"
          >
            {{ $t("datasetCreation.unique") }}
          </BaseCheckbox>
        </div>
      </div>
      
      <BaseButton
        @click="addColumn"
        class="pandera-dataframe-config__add-column"
        variant="outline"
      >
        {{ $t("datasetCreation.addColumn") }}
      </BaseButton>
    </div>
    
    <div class="pandera-dataframe-config__settings">
      <h6 class="pandera-dataframe-config__section-title">
        {{ $t("datasetCreation.schemaSettings") }}
      </h6>
      
      <BaseCheckbox
        :value="schema.strict || true"
        @input="updateSchemaProperty('strict', $event)"
      >
        {{ $t("datasetCreation.strictValidation") }}
      </BaseCheckbox>
      
      <BaseCheckbox
        :value="schema.coerce || false"
        @input="updateSchemaProperty('coerce', $event)"
      >
        {{ $t("datasetCreation.coerceTypes") }}
      </BaseCheckbox>
      
      <BaseCheckbox
        :value="schema.unique_column_names !== false"
        @input="updateSchemaProperty('unique_column_names', $event)"
      >
        {{ $t("datasetCreation.uniqueColumnNames") }}
      </BaseCheckbox>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, computed } from '@nuxtjs/composition-api';
import { PanderaDataFrameSchema } from '~/v1/infrastructure/types/PanderaSchema';

export default defineComponent({
  name: 'DatasetConfigurationPanderaDataFrame',
  props: {
    schema: {
      type: Object,
      required: true,
    },
  },
  setup(props, { emit }) {
    const schema = props.schema as PanderaDataFrameSchema;
    const dtypeOptions = [
      { value: 'str', text: 'String' },
      { value: 'int64', text: 'Integer' },
      { value: 'float64', text: 'Float' },
      { value: 'bool', text: 'Boolean' },
      { value: 'datetime64[ns]', text: 'DateTime' },
      { value: 'object', text: 'Object' },
    ];

    const updateColumnName = (oldName: string, newName: string) => {
      if (oldName === newName) return;
      
      const updatedSchema = { ...schema };
      const columnConfig = updatedSchema.columns[oldName];
      
      // Remove old column and add with new name
      delete updatedSchema.columns[oldName];
      updatedSchema.columns[newName] = columnConfig;
      
      emit('update', updatedSchema);
    };

    const updateColumnProperty = (columnName: string, property: string, value: any) => {
      const updatedSchema = { ...schema };
      updatedSchema.columns = { ...updatedSchema.columns };
      updatedSchema.columns[columnName] = {
        ...updatedSchema.columns[columnName],
        [property]: value,
      };
      
      emit('update', updatedSchema);
    };

    const updateSchemaProperty = (property: string, value: any) => {
      const updatedSchema = {
        ...schema,
        [property]: value,
      };
      
      emit('update', updatedSchema);
    };

    const addColumn = () => {
      const columnCount = Object.keys(schema.columns).length;
      const newColumnName = `column_${columnCount + 1}`;
      
      const updatedSchema = { ...schema };
      updatedSchema.columns = {
        ...updatedSchema.columns,
        [newColumnName]: {
          dtype: 'str',
          nullable: true,
          unique: false,
          coerce: false,
        },
      };
      
      emit('update', updatedSchema);
    };

    const removeColumn = (columnName: string) => {
      const updatedSchema = { ...schema };
      updatedSchema.columns = { ...updatedSchema.columns };
      delete updatedSchema.columns[columnName];
      
      emit('update', updatedSchema);
    };

    return {
      dtypeOptions,
      updateColumnName,
      updateColumnProperty,
      updateSchemaProperty,
      addColumn,
      removeColumn,
    };
  },
});
</script>

<style lang="scss" scoped>
.pandera-dataframe-config {
  &__section-title {
    margin: 0 0 0.75rem 0;
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--color-text-secondary);
  }

  &__columns {
    margin-bottom: 1.5rem;
  }

  &__column {
    border: 1px solid var(--color-border);
    border-radius: 4px;
    padding: 0.75rem;
    margin-bottom: 0.5rem;
    background-color: var(--color-background);
  }

  &__column-header {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }

  &__column-name {
    flex: 1;
  }

  &__remove-column {
    flex-shrink: 0;
  }

  &__column-config {
    display: flex;
    gap: 1rem;
    align-items: center;
    flex-wrap: wrap;
  }

  &__dtype {
    min-width: 120px;
  }

  &__add-column {
    width: 100%;
    margin-top: 0.5rem;
  }

  &__settings {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }
}
</style>