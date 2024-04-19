<template>
  <BaseLoading v-if="$fetchState.pending || $fetchState.error" />

  <BulkAnnotation
    v-else-if="
      recordCriteria.committed.page.isBulkMode &&
      recordCriteria.committed.isPending
    "
    :record-criteria="recordCriteria"
    :dataset-vectors="datasetVectors"
    :records="records"
    :record="record"
    :no-records-message="noRecordsMessage"
    :status-class="statusClass"
    @on-submit-responses="goToNext"
    @on-discard-responses="goToNext"
  />
  <FocusAnnotation
    v-else
    :record-criteria="recordCriteria"
    :dataset-vectors="datasetVectors"
    :records="records"
    :record="record"
    :no-records-message="noRecordsMessage"
    :status-class="statusClass"
    @on-submit-responses="goToNext"
    @on-discard-responses="goToNext"
  />
</template>

<script>
import { Notification } from "@/models/Notifications";
import { useRecordFeedbackTaskViewModel } from "./useRecordFeedbackTaskViewModel";

export default {
  name: "RecordFeedbackTaskAndQuestionnaireComponent",
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
      let thisRecord = this.records.getRecordOn(this.recordCriteria.committed.page);
      if (!thisRecord) {
        console.log('Record not found for recordCriteria.committed.page.client.page:', this.recordCriteria.committed.page.client.page);
        console.log('All record pages:', this.records.records.map(record => record.page));
        thisRecord = this.records.records[this.recordCriteria.committed.page.client.page-1];
      }
      return thisRecord;
    },
    metadata() {
      return this.record?.metadata;
    },
    noMoreDataMessage() {
      return `You've reached the end of the data for the ${this.recordCriteria.committed.status} queue.`;
    },
    noRecordsMessage() {
      const { status } = this.recordCriteria.committed;

      if (this.recordCriteria.isFilteredByText)
        return `You have no ${status} records matching the search input and filters`;

      return `You have no ${status} records`;
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

      Notification.dispatch("clear");

      this.fetching = true;

      const isNextRecordExist = await this.paginateRecords(this.recordCriteria);

      this.$nuxt.$emit('on-change-record-metadata', this.metadata);

      if (!isNextRecordExist) {
        setTimeout(() => {
          Notification.dispatch("notify", {
            message: this.noMoreDataMessage,
            numberOfChars: this.noMoreDataMessage.length,
            type: "info",
          });
        }, 100);
      }

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
      Notification.dispatch("clear");

      if (!this.shouldShowNotification) {
        return onFilter();
      }

      Notification.dispatch("notify", {
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
    Notification.dispatch("clear");
  },
};
</script>

<style lang="scss" scoped>
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
  &.--document-panel {
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
    color: $black-54;
  }
  &--empty {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}
</style>