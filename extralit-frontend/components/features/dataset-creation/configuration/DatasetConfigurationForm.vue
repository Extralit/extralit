<template>
  <section class="config-form">
    <div class="config-form__content">
      <div class="config-form__col-wrapper">
        <div v-if="dataset.selectedSubset.fields.length" class="config-form__col">
          <div class="config-form__col__header">
            {{ $t("datasetCreation.fields") }}
            <div v-if="dataset.subsets.length > 1" class="config-form__subset">
              {{ $t("datasetCreation.subset") }}:
              <DatasetConfigurationSelector class="config-form__selector" :options="dataset.subsets"
                :value="dataset.selectedSubset.name" @onValueChange="$emit('change-subset', $event)">
                <template slot="optionsIntro">
                  <span class="config-form__selector__intro">{{ $t("datasetCreation.selectSubset") }}</span>
                </template>
              </DatasetConfigurationSelector>
            </div>
          </div>
          <div class="config-form__col__content">
            <draggable class="config-form__draggable-area" :list="dataset.selectedSubset.fields"
              :group="{ name: 'fields' }" ghost-class="config-form__ghost" :disabled="isFocused">
              <transition-group class="config-form__draggable-area-wrapper" type="transition" :css="false">
                <DatasetConfigurationField
                  v-for="field in dataset.selectedSubset.fields.filter((f) => f.name !== dataset.mappings.external_id)"
                  :key="field.name" :field="field" :available-types="availableFieldTypes.filter((a) => a.value === 'no mapping' || a.value === field.originalType.value)
                    " @is-focused="isFocused = $event" />
              </transition-group>
            </draggable>
          </div>
        </div>
        <div v-if="dataset.importHistoryId" class="config-form__col config-form__col--metadata">
          <div class="config-form__col__header">
            {{ $t("datasetCreation.metadata") }}
          </div>
          <div class="config-form__col__content config-form__col__content--metadata">
            <DatasetConfigurationMetadataSelector :available-fields="availableMetadataFields"
              :selected-fields="selectedMetadataFields" @onSelectionChange="updateMetadataSelection" />
          </div>
        </div>
      </div>
      <div class="config-form__col-wrapper">
        <div class="config-form__col">
          <div class="config-form__col__header">
            {{ $t("datasetCreation.questionsTitle") }}
            <DatasetConfigurationAddQuestion
              :options="['text', 'label_selection', 'multi_label_selection', 'rating', 'ranking', 'span']"
              @add-question="addQuestion($event)" />
          </div>
          <div v-if="!isUpdateWorkflow" class="config-form__col__content --questions">
            <draggable v-if="dataset.selectedSubset.questions.length" class="config-form__draggable-area"
              ghost-class="config-form__ghost" :list="dataset.selectedSubset.questions" :group="{ name: 'questions' }"
              :disabled="isFocused">
              <transition-group class="config-form__draggable-area-wrapper" type="transition" :css="false">
                <DatasetConfigurationQuestion v-for="(question, index) in dataset.selectedSubset.questions"
                  :key="`question-${index}`" :selectedSubset="dataset.selectedSubset" :question="question"
                  :remove-is-allowed="true" :available-types="availableQuestionTypes"
                  @change-type="onTypeIsChanged(index, $event)" @is-focused="isFocused = $event" />
              </transition-group>
            </draggable>
          </div>
        </div>
        <div class="config-form__button-area">
          <BaseButton
            class="primary"
            @click.prevent="openCreateDatasetDialog"
            v-text="$t('datasetCreation.createButton')"
          />
          <BaseButton
            v-if="dataSource === 'import'"
            class="secondary"
            @click.prevent="openUpdateDatasetDialog"
            v-text="$t('datasetCreation.updateButton')"
          />

          <!-- Create Dataset Dialog -->
          <DatasetCreateDialog
            v-if="visibleDatasetCreationDialog"
            :dataset="dataset"
            :is-loading="isLoading"
            @close-dialog="visibleDatasetCreationDialog = false"
            @create-dataset="createDataset" />

          <!-- Update Dataset Dialog -->
          <DatasetUpdateDialog
            v-if="visibleDatasetUpdateDialog"
            :dataset="dataset"
            :is-loading="isLoading"
            @close-dialog="closeUpdateDialog"
            @update-dataset="updateDataset" />
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import { useDatasetConfigurationForm } from "./useDatasetConfigurationForm";
import { MetadataCreation } from "~/v1/domain/entities/hub/MetadataCreation";

export default {
  props: {
    dataset: {
      type: Object,
      required: true,
    },
    dataSource: {
      type: String,
      default: "hub",
      validator: (value) => ["hub", "import"].includes(value),
    },
  },
  data() {
    return {
      isFocused: false,
      visibleDatasetCreationDialog: false,
      visibleDatasetUpdateDialog: false,
      selectedMetadataFields: [],
      isUpdateWorkflow: false,
    };
  },
  computed: {
    getMaxNumberInNames() {
      return Math.max(
        ...this.dataset.selectedSubset.questions.map((question: any) => {
          const numberInName = question.name.split("_").pop();
          return parseInt(numberInName) || 0;
        })
      );
    },
    availableMetadataFields() {
      // Get available fields from ImportHistory if available
      if (this.dataset.importHistoryId && this.dataset.availableFields) {
        return this.dataset.availableFields;
      }
      // Fallback to field names from the dataset
      return this.dataset.selectedSubset.fields.map((f: any) => f.name);
    },
    // Extract field schema information from the dataset for compatibility API
    datasetFieldSchema() {
      return this.dataset.selectedSubset.fields.map(field => ({
        name: field.name,
        type: field.originalType?.value || field.type?.value || 'string'
      }));
    },
    // Get column names for compatibility checking
    columnNames() {
      return this.dataset.selectedSubset.fields.map(f => f.name);
    },
  },
  methods: {
    createDataset() {
      this.create(this.dataset);
    },
    openCreateDatasetDialog() {
      this.visibleDatasetCreationDialog = true;
    },
    openUpdateDatasetDialog() {
      this.isUpdateWorkflow = true;
      this.visibleDatasetUpdateDialog = true;
    },
    closeUpdateDialog() {
      this.isUpdateWorkflow = false;
      this.visibleDatasetUpdateDialog = false;
    },
    updateDataset(updateData) {
      this.closeUpdateDialog();

      // Use the source dataset from the dialog event, or fall back to this.dataset
      const sourceDataset = updateData.source || this.dataset;
      this.update(sourceDataset, updateData.targetDataset.id);
    },
    generateName(type: string, number: string | number): string {
      const typeName = this.$t(`config.questionId.${type}`);
      return `${typeName}_${parseInt(number as string) || 0}`;
    },
    addQuestion(type: string) {
      const questionName = this.generateName(type, this.getMaxNumberInNames + 1);
      this.dataset.selectedSubset.addQuestion(questionName, {
        type,
      });
    },
    onTypeIsChanged(questionIndex: number, type: any) {
      const question = this.dataset.selectedSubset.questions[questionIndex];
      if (!question) return;

      const numberInName = question.name.split("_").pop();
      this.dataset.selectedSubset.removeQuestion(question.name);
      const newQuestionName = this.generateName(type.value, numberInName);
      this.dataset.selectedSubset.addQuestion(
        newQuestionName,
        {
          type: type.value,
        },
        questionIndex
      );
    },
    updateMetadataSelection(selectedFields: string[]) {
      this.selectedMetadataFields = selectedFields;
      this.updateDatasetMetadata(selectedFields);
    },
    updateDatasetMetadata(selectedFields: string[]) {
      // Clear existing metadata
      this.dataset.selectedSubset.metadata.length = 0;

      // Add selected fields as metadata
      selectedFields.forEach((fieldName: string) => {
        const metadata = MetadataCreation.from(fieldName, "terms");
        if (metadata) {
          this.dataset.selectedSubset.metadata.push(metadata);
        }
      });
    },
  },
  mounted() {
    if (this.dataset.importHistoryId) {
      const defaultMetadataFields = ["reference", "doi", "pmid"];
      const availableDefaults = this.availableMetadataFields.filter((field: string) => defaultMetadataFields.includes(field));
      this.updateMetadataSelection(availableDefaults);
    }
  },
  setup() {
    return useDatasetConfigurationForm();
  },
};
</script>

<style lang="scss" scoped>
.config-form {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: $base-space;
  padding: $base-space * 2;

  &__content {
    display: flex;
    gap: $base-space * 2;
    min-height: 0;
    height: 100%;

    @include media("<tablet") {
      flex-direction: column;
    }
  }

  &__col-wrapper {
    display: flex;
    flex-direction: column;
    gap: $base-space * 2;
    position: relative;
    width: 100%;
    max-width: 440px;
  }

  &__col {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    background: var(--bg-accent-grey-1);
    border: 1px solid var(--bg-opacity-6);
    border-radius: $border-radius-m;

    // For metadata column, don't stretch to fill height
    &--metadata {
      height: auto;
      flex-shrink: 0;
    }

    &__header {
      display: flex;
      justify-content: space-between;
      min-height: $base-space * 7;
      align-items: center;
      padding: $base-space * 2 $base-space * 2 $base-space $base-space * 2;
      font-weight: 500;
    }

    &__content {
      display: flex;
      flex-direction: column;
      padding: $base-space $base-space * 2 $base-space * 2;
      gap: $base-space;
      overflow: auto;
      height: 100%;

      // For metadata selector, don't stretch to fill height
      &--metadata {
        height: auto;
        flex-shrink: 0;
      }
    }
  }

  &__draggable-area {
    display: flex;
    flex-direction: column;
    gap: $base-space;
  }

  &__draggable-area-wrapper {
    display: flex;
    flex-direction: column;
    gap: $base-space;
  }

  &__ghost {
    opacity: 0.5;
  }

  &__selector {
    &__intro {
      display: block;
      padding: 4px;
      background: var(--bg-config-alert);
      @include font-size(12px);
      @include line-height(16px);
    }
  }

  &__subset {
    display: flex;
    gap: $base-space;
    align-items: center;
    font-weight: 400;
  }

  &__button-area {
    display: flex;
    gap: 1rem;

    .button {
      width: 100%;
      justify-content: center;
    }
  }
}
</style>
