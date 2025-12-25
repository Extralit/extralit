<template>
  <div>
    <div class="table-config">
      <div class="table-config__header">
        <label class="table-config__label">
          {{ $t('datasetCreation.questions.table.columns') }}
        </label>
        <BaseButton class="table-config__add-btn" @click="addColumn">
          {{ $t('datasetCreation.questions.table.addColumn') }}
        </BaseButton>
      </div>

      <div class="table-config__columns">
        <div
          v-for="(column, index) in columns"
          :key="index"
          class="table-config__column"
          :class="{ '--error': hasColumnError(index) }"
        >
          <div class="table-config__column-inputs">
            <input
              type="text"
              :value="column.name"
              @input="updateColumnName(index, $event.target.value)"
              @focus.stop="onFocus"
              @blur="onBlur"
              :placeholder="$t('datasetCreation.questions.table.columnName')"
              class="table-config__input table-config__input--name"
            />
            <input
              type="text"
              :value="column.title"
              @input="updateColumnTitle(index, $event.target.value)"
              @focus.stop="onFocus"
              @blur="onBlur"
              :placeholder="$t('datasetCreation.questions.table.columnTitle')"
              class="table-config__input table-config__input--title"
            />
            <BaseButton
              v-if="columns.length > 1"
              class="table-config__remove-btn"
              @click="removeColumn(index)"
            >
              <svgicon name="close" />
            </BaseButton>
          </div>
        </div>
      </div>

      <Validation v-if="errors.options?.length" :validations="errors.options" />
      <label
        v-else
        class="table-config__help"
        v-text="$t('datasetCreation.questions.table.helpText')"
      />
    </div>
  </div>
</template>

<script>
import 'assets/icons/close';

export default {
  data() {
    return {
      errors: {},
      isDirty: false,
    };
  },
  props: {
    question: {
      type: Object,
      required: true,
    },
  },
  computed: {
    columns() {
      return this.question.settings.options || [];
    },
  },
  methods: {
    validateOptions() {
      this.errors = this.question.validate();
    },
    onFocus() {
      this.$emit('is-focused', true);
    },
    onBlur() {
      this.isDirty = true;
      this.validateOptions();
      this.$emit('is-focused', false);
    },
    hasColumnError(index) {
      return this.errors.options?.length && !this.columns[index]?.name;
    },
    updateColumnName(index, value) {
      const columns = [...this.columns];
      columns[index] = {
        ...columns[index],
        name: value,
      };
      this.question.settings.options = columns;

      if (this.isDirty) {
        this.validateOptions();
      }
    },
    updateColumnTitle(index, value) {
      const columns = [...this.columns];
      columns[index] = {
        ...columns[index],
        title: value,
      };
      this.question.settings.options = columns;

      if (this.isDirty) {
        this.validateOptions();
      }
    },
    addColumn() {
      const columnNumber = this.columns.length + 1;
      const columns = [
        ...this.columns,
        {
          name: `column${columnNumber}`,
          title: `Column ${columnNumber}`,
          description: '',
        },
      ];
      this.question.settings.options = columns;

      if (this.isDirty) {
        this.validateOptions();
      }
    },
    removeColumn(index) {
      const columns = [...this.columns];
      columns.splice(index, 1);
      this.question.settings.options = columns;

      if (this.isDirty) {
        this.validateOptions();
      }
    },
  },
};
</script>

<style lang="scss" scoped>
$error-color: hsl(3, 100%, 69%);

.table-config {
  display: flex;
  flex-direction: column;
  gap: $base-space;

  &__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  &__label {
    color: var(--fg-secondary);
    @include font-size(12px);
    font-weight: 600;
  }

  &__add-btn.button {
    padding: calc($base-space / 2) $base-space;
    @include font-size(12px);
    background: var(--bg-cuaternary);
    color: var(--fg-on-dark);
    border-radius: $border-radius;

    &:hover {
      background: var(--bg-cuaternary-highlight);
    }
  }

  &__columns {
    display: flex;
    flex-direction: column;
    gap: $base-space;
  }

  &__column {
    display: flex;
    flex-direction: column;

    &.--error {
      .table-config__input {
        border-color: $error-color;
      }
    }
  }

  &__column-inputs {
    display: flex;
    gap: $base-space;
    align-items: center;
  }

  &__input {
    flex: 1;
    height: calc($base-space * 4);
    padding: 0 $base-space;
    border-radius: $border-radius;
    border: 1px solid var(--bg-opacity-10);
    background: var(--bg-accent-grey-1);
    outline: none;
    color: var(--fg-secondary);
    @include font-size(12px);

    &:focus {
      border-color: var(--fg-cuaternary);
    }

    @include input-placeholder {
      color: var(--fg-tertiary);
    }

    &--name {
      flex: 0 0 150px;
    }
  }

  &__remove-btn.button {
    padding: $base-space / 2;
    background: transparent;
    color: var(--fg-tertiary);

    &:hover {
      color: var(--fg-error);
    }

    .svg-icon {
      width: 16px;
      height: 16px;
    }
  }

  &__help {
    color: var(--fg-secondary);
    @include font-size(12px);
  }
}
</style>
