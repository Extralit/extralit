<template>
  <BaseLoading v-if="$fetchState.pending || $fetchState.error" />

  <BulkAnnotation
    v-else-if="
      recordCriteria.committed.page.isBulkMode &&
      recordCriteria.committed.isPending
    "
    role="main"
    :record-criteria="recordCriteria"
    :dataset-vectors="datasetVectors"
    :records="records"
    :record="record"
    :records-message="recordsMessage"
    :status-class="statusClass"
    @on-submit-responses="goToNext"
    @on-discard-responses="goToNext"
  />
  <FocusAnnotation
    v-else
    role="main"
    :record-criteria="recordCriteria"
    :dataset-vectors="datasetVectors"
    :records="records"
    :record="record"
    :records-message="recordsMessage"
    :status-class="statusClass"
    @on-submit-responses="goToNext"
    @on-discard-responses="goToNext"
  />
</template>

<script>
import { useRecordFeedbackTaskViewModel } from "./useRecordFeedbackTaskViewModel";

export default {
  name: "RecordFeedbackTaskAndQuestionnaire",
  props: {
    recordCriteria: {
      type: Object,
      required: true,
    },
  },
  data() {
    return {
      fetching: false,
      isDocumentPanelOn: false,
    };
  },
  computed: {
    record() {
      return this.records.getRecordOn(this.recordCriteria.committed.page);
    },
    metadata() {
      return this.record?.metadata;
    },
    statusClass() {
      return `--${this.record?.status}`;
    },
    shouldShowNotification() {
      return this.record?.isSubmitted && this.record?.isModified;
    },
  },
  async fetch() {
    await this.onLoadRecords();
  },
  methods: {
    async onLoadRecords() {
      if (this.fetching) return Promise.resolve();

      this.fetching = true;

      await this.loadRecords(this.recordCriteria);

      this.$nuxt.$emit('on-change-record-metadata', this.metadata);

      this.fetching = false;
    },
    async paginate() {
      if (this.fetching) return Promise.resolve();

      this.$notification.clear();

      this.fetching = true;

      await this.paginateRecords(this.recordCriteria);

      this.$nuxt.$emit('on-change-record-metadata', this.metadata);

      this.fetching = false;
    },
    onChangeRecordPage(criteria) {
      const filter = async () => {
        await this.paginate();
      };

      this.showNotificationForNewFilterWhenIfNeeded(filter, () =>
        criteria.rollback()
      );
    },
    onChangeRecordFilter(criteria) {
      const filter = async () => {
        await this.onLoadRecords();
      };

      this.showNotificationForNewFilterWhenIfNeeded(filter, () =>
        criteria.rollback()
      );
    },
    goToNext() {
      this.recordCriteria.nextPage();

      this.paginate();
    },
    showNotificationForNewFilterWhenIfNeeded(onFilter, onClose) {
      this.$notification.clear();

      if (!this.shouldShowNotification) {
        return onFilter();
      }

      this.$notification.notify({
        message: this.$t("changes_no_submit"),
        buttonText: this.$t("button.ignore_and_continue"),
        permanent: true,
        type: "warning",
        onClick() {
          return onFilter();
        },
        onClose() {
          return onClose();
        },
      });
    },
  },
  setup(props) {
    return useRecordFeedbackTaskViewModel(props);
  },
  mounted() {
    this.$root.$on("on-change-record-page", this.onChangeRecordPage);

    this.$root.$on(
      "on-change-record-criteria-filter",
      this.onChangeRecordFilter
    );
  },
  destroyed() {
    this.$root.$off("on-change-record-page");
    this.$root.$off("on-change-record-criteria-filter");
    this.$notification.clear();
  },
};
</script>

<!-- <style lang="scss" scoped>
.wrapper {
  display: flex;
  flex-wrap: wrap;
  height: 100%;
  gap: $base-space * 2;
  padding: $base-space * 2;

  @include media("<desktop") {
    flex-flow: column;
    overflow: auto;
  }
  &__records,
  &__form {
    @include media("<desktop") {
      overflow: visible;
      height: auto;
      max-height: none !important;
    }
  }
  &__records {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: $base-space;
    height: 100%;
    min-width: 0;
  }
  &__text {
    color: var(--bg-opacity-54);
  }
  &--empty {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}
</style> -->
