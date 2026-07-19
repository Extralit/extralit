<template>
  <section class="review-record" :data-record="record.recordId">
    <header class="review-record__header">
      <h3>{{ record.schemaName }}</h3>
    </header>

    <div v-if="record.contextFields.length" class="review-record__context">
      <h4 v-text="$t('review.context')" />
      <dl>
        <template v-for="field in record.contextFields" :key="field.column.name">
          <dt>{{ field.column.name }}</dt>
          <dd>{{ formatContext(field) }}</dd>
        </template>
      </dl>
    </div>

    <ReviewCellInput
      v-for="cell in record.cells"
      :key="cell.question.id"
      :cell="cell"
      :model-value="values[cell.question.name]"
      :table-columns="tableColumnsFor(cell)"
      @update:model-value="setValue(cell.question.name, $event)"
    />

    <div v-if="record.orphanedValues.length" class="review-record__orphans">
      <h4 v-text="$t('review.orphanedValues')" />
      <dl>
        <template v-for="orphan in record.orphanedValues" :key="orphan.name">
          <dt>{{ orphan.name }}</dt>
          <dd>{{ JSON.stringify(orphan.value) }}</dd>
        </template>
      </dl>
    </div>

    <ul v-if="errors.length" class="review-record__errors">
      <li v-for="message in errors" :key="message">{{ message }}</li>
    </ul>

    <footer class="review-record__actions">
      <BaseButton
        class="primary"
        :data-test="`submit-${record.recordId}`"
        @click="$emit('submit', record.recordId, cleanValues())"
      >
        {{ $t("review.submit") }}
      </BaseButton>
      <BaseButton
        class="secondary"
        :data-test="`save-draft-${record.recordId}`"
        @click="$emit('save-draft', record.recordId, cleanValues())"
      >
        {{ $t("review.saveDraft") }}
      </BaseButton>
      <BaseButton
        class="secondary"
        :data-test="`discard-${record.recordId}`"
        @click="$emit('discard', record.recordId)"
      >
        {{ $t("review.discard") }}
      </BaseButton>
    </footer>
  </section>
</template>

<script lang="ts">
import { defineComponent, reactive, watch, type PropType } from "vue";
import { type ContextField, type ReviewCell, ReviewRecord } from "~/v2/domain/entities/review/ReferenceReview";
import { type ColumnMeta } from "~/v2/domain/entities/schema/ColumnMeta";
import ReviewCellInput from "./ReviewCellInput.vue";

export default defineComponent({
  name: "ReviewRecordCard",
  components: { ReviewCellInput },
  props: {
    record: { type: Object as PropType<ReviewRecord>, required: true },
    errors: { type: Array as PropType<string[]>, default: () => [] },
    columnsCache: { type: Array as PropType<ColumnMeta[]>, default: () => [] },
  },
  emits: ["submit", "save-draft", "discard"],
  setup(props) {
    const values = reactive<Record<string, unknown>>(props.record.initialValues());

    watch(
      () => props.record,
      (record) => {
        Object.keys(values).forEach((key) => delete values[key]);
        Object.assign(values, record.initialValues());
      }
    );

    const setValue = (name: string, value: unknown) => {
      values[name] = value;
    };

    // Plain values keyed by question name; nulls dropped so "no answer" stays absent
    // (submit-time required-question enforcement is the server's, surfaced via errors).
    const cleanValues = (): Record<string, unknown> =>
      Object.fromEntries(Object.entries(values).filter(([, v]) => v !== null && v !== undefined && v !== ""));

    const tableColumnsFor = (cell: ReviewCell): ColumnMeta[] =>
      props.columnsCache.filter((column) => cell.question.columns.includes(column.name));

    const formatContext = (field: ContextField): string =>
      field.value === null || field.value === undefined ? "—" : String(field.value);

    return { values, setValue, cleanValues, tableColumnsFor, formatContext };
  },
});
</script>

<style lang="scss" scoped>
.review-record {
  border: 1px solid var(--bg-opacity-10);
  border-radius: $border-radius;
  padding: $base-space * 2;
  margin-bottom: $base-space * 2;

  &__errors {
    color: var(--color-danger, #c00);
  }

  &__actions {
    display: flex;
    gap: $base-space;
    margin-top: $base-space * 2;
  }

  &__context dl,
  &__orphans dl {
    display: grid;
    grid-template-columns: max-content 1fr;
    gap: 2px $base-space * 2;
    color: var(--fg-secondary);
  }
}
</style>
