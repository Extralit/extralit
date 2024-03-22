<template>
  <div class="wrapper">
    <div class="header">
      <h2 class="--heading5 --medium description__title" v-html="title" />
    </div>
    <div class="content">
      <BaseSpinner v-if="isLoading" />

      <BaseFeedbackComponent v-if="isFeedbackVisible && !isLoading" :feedbackInput="feedbackInput"
        @on-click="feedbackAction" class="feedback-area" />

      <TokenClassificationGlobalLabelsComponent v-if="isTaskTokenClassification && numberOfLabels && !isLoading"
        :labels="labels" :showAllLabels="showAllLabels"
        @on-toggle-show-less-more-labels="showAllLabels = !showAllLabels" />

      <TextClassificationGlobalLabelsComponent v-if="isTaskTextClassification && numberOfLabels && !isLoading"
        :labels="labels" :showAllLabels="showAllLabels"
        @on-toggle-show-less-more-labels="showAllLabels = !showAllLabels" />

      <div class="buttons-area" v-if="allowAddNewLabel">
        <InputAction text="+ Add label" placeholder="New label" button="Create" @input="onAddNewLabels" />
        <!-- <InputAction text="- Remove label" placeholder="Label to remove" button="Remove"
          @input="onRemoveNewLabels" /> -->
        <!-- <BaseButton @on-click.prevent="test">TEST</BaseButton> -->
      </div>
    </div>
  </div>
</template>

<script>
import { mapActions } from "vuex";
import { useRole } from "@/v1/infrastructure/services";
import { getDatasetFromORM } from "@/models/dataset.utilities";
import {
  getAllLabelsByDatasetId,
  getLabelsNotSavedInBackByDatasetId,
  isExistAnyLabelsNotSavedInBackByDatasetId,
} from "@/models/globalLabel.queries";

export default {
  name: "EditionLabelComponent",
  props: {
    title: {
      type: String,
      default: () => "Labels",
    },
    datasetId: {
      type: Array,
      required: true,
    },
    datasetTask: {
      type: String,
      required: true,
    },
    isLoading: {
      type: Boolean,
      default: () => true,
    },
  },
  data() {
    return {
      isSortAsc: true,
      sortBy: "order",
      characterToSeparateLabels: null,
      saveLabelsButtonLabel: "Save labels",
      inputForSaveSchemaFeedback: {
        message: `Action needed: Save labels to validate the annotation schema. More in
            <a target='_blank' href='${this.$config.documentationSiteLabelScheme}'>
              docs</a>.
          `,
        buttonLabels: [{ label: "Save labels", value: "SAVE_LABEL_SCHEMA" }],
        feedbackType: "ERROR",
      },
      inputForEmptyLabelsFeedback: {
        message:
          "You still have no labels in your dataset, start by creating some",
        feedbackType: "ERROR",
      },
      showAllLabels: false,
    };
  },
  computed: {
    allowAddNewLabel() {
      return this.isAdminOrOwnerRole;
    },
    dataset() {
      return getDatasetFromORM(this.datasetId, this.datasetTask, false);
    },
    datasetName() {
      return this.dataset?.name;
    },
    isTaskTokenClassification() {
      return this.datasetTask === "TokenClassification";
    },
    isTaskTextClassification() {
      return this.datasetTask === "TextClassification";
    },
    labels() {
      return getAllLabelsByDatasetId(
        this.datasetId,
        this.sortBy,
        this.isSortAsc
      );
    },
    numberOfLabels() {
      return this.labels.length;
    },
    labelsInGlobalLabelsNotSavedInBack() {
      return getLabelsNotSavedInBackByDatasetId(this.datasetId);
    },
    labelsTextNotSavedInBack() {
      return this.labelsInGlobalLabelsNotSavedInBack.reduce(
        (acc, curr) => acc.concat(curr.text),
        []
      );
    },
    isAnyLabelsInGlobalLabelsModelNotSavedInBack() {
      return isExistAnyLabelsNotSavedInBackByDatasetId(this.datasetId);
    },
    feedbackInput() {
      if (this.isFeedbackVisible) {
        return (
          this.feedbackInputIfThereIsLabelsNotSavedInBack ||
          this.feedbackInputIfThereAreNotLabels
        );
      }
      return null;
    },
    isFeedbackVisible() {
      return (
        this.feedbackInputIfThereIsLabelsNotSavedInBack ||
        this.feedbackInputIfThereAreNotLabels
      );
    },
    feedbackInputIfThereIsLabelsNotSavedInBack() {
      if (this.isAnyLabelsInGlobalLabelsModelNotSavedInBack) {
        return this.inputForSaveSchemaFeedback;
      }
      return null;
    },
    feedbackInputIfThereAreNotLabels() {
      if (!this.numberOfLabels) {
        return this.inputForEmptyLabelsFeedback;
      }
      return null;
    },
  },
  methods: {
    ...mapActions({
      onAddNewLabelsInDataset: "entities/datasets/onAddNewLabels",
    }),
    async onAddNewLabels(newLabelsString) {
      const newLabels = this.splitTrimArrayString(
        newLabelsString,
        this.characterToSeparateLabels
      );
      try {
        await this.onAddNewLabelsInDataset({
          datasetId: this.datasetId,
          datasetTask: this.datasetTask,
          newLabels,
        });
        this.toggleShowAllLabels(true);
      } catch (err) {
        console.log(err);
      }
    },
    async onSaveLabelsNotPersisted() {
      const newLabels = this.labelsTextNotSavedInBack;
      try {
        await this.onAddNewLabelsInDataset({
          datasetId: this.datasetId,
          datasetTask: this.datasetTask,
          newLabels,
        });
        this.toggleShowAllLabels(true);
      } catch (err) {
        console.log(err);
      }
    },
    splitTrimArrayString(labels, splitCharacter = null) {
      return labels.split(splitCharacter).map((item) => item.trim());
    },
    toggleShowAllLabels(trueOrFalse) {
      this.showAllLabels = trueOrFalse;
    },
    feedbackAction() {
      if (this.isAnyLabelsInGlobalLabelsModelNotSavedInBack) {
        return this.onSaveLabelsNotPersisted();
      }
      return null;
    },
    test() {
      console.log("TEST");
      console.log(this.datasetId);
    },
  },
  setup() {
    const { isAdminOrOwnerRole } = useRole();
    return { isAdminOrOwnerRole };
  },
};
</script>

<style lang="scss" scoped>
.wrapper {
  display: flex;
  flex-direction: column;
  .header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
  }
  .content {
    display: flex;
    flex-direction: column;
    gap: 15px;
  }
}

.feedback-area {
  display: inline-flex;
  margin-bottom: $base-space * 5;
}

.buttons-area {
  display: flex;
  align-items: baseline;
  gap: 100px;
}
</style>
