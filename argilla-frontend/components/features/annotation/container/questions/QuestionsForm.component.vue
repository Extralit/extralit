<template>
  <form
    class="questions-form"
    :class="questionFormClass"
    @submit.stop.prevent=""
    v-click-outside="onClickOutside"
    @click="focusOnFirstQuestionFromOutside"
  >
    <div class="questions-form__content">
      <div class="questions-form__content__edge"></div>
      <div class="questions-form__header">
        <p class="questions-form__guidelines-link">
          <div v-if="isDraftSaving" class="questions-form__status">
            <svgicon color="#0000005e" name="refresh" />
            {{ $t("saving") }}
          </div>
          <div v-else-if="record.isDraft" class="questions-form__status">
            {{ $t("saved") }}
            <BaseDate
              class="tooltip"
              v-if="record.updatedAt"
              :date="record.updatedAt?.toLocaleString()"
              format="date-relative-now"
              :updateEverySecond="10"
            />
          </div>

          <NuxtLink
            :to="{
              name: 'dataset-id-settings',
              params: { id: datasetId },
            }"
            target="_blank"
            >{{ $t("annotationGuidelines") }}
            <svgicon name="external-link" width="12" />
          </NuxtLink>
        </p>
      </div>

      <QuestionsComponent
        :questions="record.questions"
        :autofocusPosition="autofocusPosition"
        :is-bulk-mode="isBulkMode"
        @on-focus="updateQuestionAutofocus"
      />
    </div>
    <div class="footer-form">
      <div class="footer-form__content">
        <BaseButton
          v-if="showDiscardButton || isDiscarding"
          type="button"
          class="button--discard"
          :class="isDiscarding ? '--button--discarding' : null"
          :loading="isDiscarding"
          :loading-progress="progress"
          :disabled="isDiscardDisabled || isSaving"
          :data-title="!isSaving ? draftSavingTooltip : null"
          @on-click="onDiscard"
        >
          <span
            v-if="!isDiscarding"
            class="button__shortcuts"
            v-text="'⌫'"
          /><span v-text="$t('questions_form.discard')" />
        </BaseButton>
        <BaseButton
          type="button"
          class="button--draft"
          :loading-progress="progress"
          :disabled="isDraftSaveDisabled || isSaving"
          :data-title="!isSaving ? draftSavingTooltip : null"
          @on-click="onSaveDraft"
        >
          <span v-if="!isDraftSaving"
            ><span
              class="button__shortcuts"
              v-text="$platform.isMac ? '⌘' : 'ctrl'" /><span
              class="button__shortcuts"
              v-text="'S'"
          /></span>
          <span v-text="$t('questions_form.draft')" />
        </BaseButton>
        <BaseButton
          type="submit"
          class="button--submit"
          :class="[
            isSubmitting ? '--button--submitting' : null,
            isDiscarding || isDraftSaving ? '--button--remove-bg' : null,
          ]"
          :loading-progress="progress"
          :loading="isSubmitting"
          :disabled="
            !questionAreCompletedCorrectly || isSubmitDisabled || isSaving
          "
          :data-title="
            !isSaving
              ? !questionAreCompletedCorrectly && !isSubmitDisabled
                ? $t('to_submit_complete_required')
                : submitTooltip
              : null
          "
          @on-click="onSubmit"
        >
          <span v-if="!isSubmitting" class="button__shortcuts" v-text="'↵'" />
          <span v-text="$t('questions_form.submit')" />
        </BaseButton>
      </div>
    </div>
  </form>
</template>

<script>
import "assets/icons/external-link";
import "assets/icons/refresh";
import interact from 'interactjs'

export default {
  props: {
    datasetId: {
      type: String,
      required: true,
    },
    record: {
      type: Object,
      required: true,
    },
    showDiscardButton: {
      type: Boolean,
      default: true,
    },
    areActionsEnabled: {
      type: Boolean,
      default: true,
    },
    isSubmitting: {
      type: Boolean,
      required: true,
    },
    isDiscarding: {
      type: Boolean,
      required: true,
    },
    isDraftSaving: {
      type: Boolean,
      required: true,
    },
    isSubmitDisabled: {
      type: Boolean,
      default: false,
    },
    isDiscardDisabled: {
      type: Boolean,
      default: false,
    },
    isDraftSaveDisabled: {
      type: Boolean,
      default: false,
    },
    submitTooltip: {
      type: String,
      default: null,
    },
    discardTooltip: {
      type: String,
      default: null,
    },
    draftSavingTooltip: {
      type: String,
      default: null,
    },
    progress: {
      type: Number,
      default: 0,
    },
    enableAutoSubmitWithKeyboard: {
      type: Boolean,
      default: false,
    },
    isBulkMode: {
      type: Boolean,
      default: false,
    },
  },
  
  data() {
    return {
      autofocusPosition: 0,
      interactionCount: 0,
      isSubmittedTouched: false,
      userComesFromOutside: false,
      timer: null,
      duration: { value: 0 },
    };
  },

  computed: {
    questionFormClass() {
      if (this.isSubmitting) return "--submitting --waiting";
      if (this.isDiscarding) return "--discarding --waiting";
      // if (this.isDraftSaving) return "--saving-draft";
      if (this.isDraftSaving) return;

      if (
        this.isSubmittedTouched ||
        (this.formHasFocus && this.interactionCount > 1)
      )
        return "--focused-form";
    },
    formHasFocus() {
      return this.autofocusPosition || this.autofocusPosition == 0;
    },
    numberOfQuestions() {
      return this.record.questions.length;
    },
    questionAreCompletedCorrectly() {
      return this.record.questionAreCompletedCorrectly();
    },
    isSaving() {
      return this.isDraftSaving || this.isDiscarding || this.isSubmitting;
    },
  },

  watch: {
    record: {
      deep: true,
      immediate: true,
      handler() {
        this.isSubmittedTouched = this.record.isSubmitted && this.record.isModified;
        if (this.duration.value > 1) {
          this.checkAndSaveDraft();
        }
      },
    },
  },

  mounted() {
    // Listen for visibility change events
    document.addEventListener("keydown", this.handleGlobalKeys);
    this.startTimer();
    document.addEventListener('visibilitychange', this.handleVisibilityChange);

    interact(this.$el)
      .resizable({
        edges: { left: true, right: false, bottom: false, top: false },
        modifiers: [
          interact.modifiers.restrictSize({
            min: { width: 200, height: 0 },
          }),
        ],
      })
      .on('resizemove', event => {
        let target = event.target;
        let newWidth = event.rect.width;
        let parentWidth = target.parentElement.offsetWidth;
        let clampedWidth = Math.max(Math.min(newWidth, 0.8 * parentWidth), 0.25 * parentWidth);

        requestAnimationFrame(() => {
          target.style.width = clampedWidth + 'px';
          document.documentElement.style.setProperty('--questions-form-width', target.style.width);
        });
      });
  },

  beforeDestroy() {
    this.stopTimer();
    document.removeEventListener('visibilitychange', this.handleVisibilityChange);
    document.removeEventListener("keydown", this.handleGlobalKeys);
  },

  methods: {
    async autoSubmitWithKeyboard(key) {
      if (!this.enableAutoSubmitWithKeyboard) return;
      if (!this.record.isModified) return;
      if (this.record.questions.length > 1) return;
      if (isNaN(parseInt(key))) return;

      const question = this.record.questions[0];

      if (question.isSingleLabelType || question.isRatingType) {
        await this.onSubmit();
      }
    },
    focusOnFirstQuestionFromOutside(event) {
      if (!this.userComesFromOutside) return;
      if (event.srcElement.id || event.srcElement.getAttribute("for")) return;

      this.userComesFromOutside = false;
      this.updateQuestionAutofocus(0);
    },
    focusOnFirstQuestion(event) {
      event.preventDefault();
      this.updateQuestionAutofocus(0);
    },
    onClickOutside() {
      this.autofocusPosition = null;
      this.userComesFromOutside = true;
    },
    handleGlobalKeys(event) {
      const { code, ctrlKey, metaKey, shiftKey, key } = event;

      if (shiftKey) return;

      if (code === "Tab" && this.userComesFromOutside) {
        this.focusOnFirstQuestion(event);

        return;
      }

      if (!this.areActionsEnabled) return;

      switch (code) {
        case "KeyS": {
          if (this.$platform.isMac) {
            if (!metaKey) return;
          } else if (!ctrlKey) return;

          event.preventDefault();
          event.stopPropagation();
          this.onSaveDraft();

          break;
        }
        case "Enter": {
          if (this.$platform.isMac) {
            if (!metaKey) return;
          } else if (!ctrlKey) return;
          this.onSubmit();
          break;
        }
        case "Backspace": {
          if (this.$platform.isMac) {
            if (!metaKey) return;
          } else if (!ctrlKey) return;
          this.onDiscard();
          break;
        }
        default: {
          this.autoSubmitWithKeyboard(key);
          break;
        }
      }
    },
    onSubmit() {
      if (
        this.isSubmitDisabled ||
        this.isSaving ||
        !this.questionAreCompletedCorrectly
      )
        return;

        this.$emit("on-submit-responses", this.duration);
    },
    onDiscard() {
      if (this.isDiscardDisabled || this.isSaving) return;

      this.$emit("on-discard-responses");
    },
    checkAndSaveDraft() {
      if (this.isDraftSaveDisabled || this.isSaving) {
        return;
      }
      const modified = this.record.getModified();
      const condition = modified?.questions?.some(
        question => {
          const conditionForThisQuestion = question && question.answer && (
            question.answer?.value || 
            question.answer?.values?.some(value => !!value)
          );
          return conditionForThisQuestion;
        });

      if (modified && condition) {
        this.onSaveDraft();
      }
    },
    onSaveDraft() {
      if (this.isDraftSaveDisabled || this.isSaving) return;

      this.$emit("on-save-draft", this.duration);
    },
    updateQuestionAutofocus(index) {
      this.interactionCount++;
      this.autofocusPosition = Math.min(
        this.numberOfQuestions - 1,
        Math.max(0, index)
      );
    },
    startTimer() {
      this.timer = setInterval(() => {
        this.duration.value++;
      }, 1000);
    },
    stopTimer() {
      clearInterval(this.timer);
      this.timer = null;
    },
    resetTimer() {
      this.duration.value = 0;
    },
    handleVisibilityChange() {
      if (document.hidden) {
        this.stopTimer();
      } else {
        this.startTimer();
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.questions-form {
  display: flex;
  flex-direction: column;
  width: var(--questions-form-width);
  flex-shrink: 0;
  gap: $base-space;
  max-height: 100%;
  min-width: 0;
  justify-content: space-between;
  margin-bottom: auto;
  @include media("<desktop") {
    justify-content: flex-start;
    width: 100%;
  }
  &__header {
    display: flex;
    justify-content: right;
  }
  &__status {
    position: absolute;
    left: $base-space * 2;
    @include font-size(14px);
    color: $black-37;
  }
  &__guidelines-link {
    margin: 0;
    @include font-size(14px);
    color: $black-37;
    a {
      color: $black-37;
      outline: 0;
      text-decoration: none;
      &:hover,
      &:focus {
        color: $black-54;
        transition: color 0.2s ease-in-out;
      }
    }
  }
  &__content {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: $base-space * 2;
    padding: $base-space * 2;
    overflow: auto;
    scroll-behavior: smooth;
    border-radius: $border-radius-m;
    border: 1px solid transparent;
    background: palette(white);
    .--pending & {
      border-color: $black-10;
    }
    .--draft &,
    .--saving-draft & {
      border-color: $draft-color;
    }
    .--discarded &,
    .--discarding & {
      border-color: $discarded-color;
    }
    .--submitted &,
    .--submitting & {
      border-color: $submitted-color;
    }
    .--saving-draft & {
      box-shadow: 0 0 0 1px $draft-color;
    }
    .--discarding & {
      box-shadow: 0 0 0 1px $discarded-color;
    }
    .--submitting & {
      box-shadow: 0 0 0 1px $submitted-color;
    }
    .--waiting & {
      opacity: 0.7;
    }
    &__edge {
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 3px;
      height: 100%;
      z-index: 1;
      background: transparent;
      opacity: 0;
      transition: background 0.3s ease;

      &::before {
        content: "";
        position: absolute;
        top: 0;
        bottom: 0;
        left: -15px;
        width: 30px;
        height: 100%;
        background: transparent;
      }

      &:hover {
        background: $primary-lighten-color;
        opacity: 1;
      }
    }
  }
}

.footer-form {
  &__content {
    display: flex;
    flex-direction: row;
    justify-content: space-between;
    align-items: stretch;
    border-radius: $border-radius-m;
    background: #f0f2fa;
    container-type: inline-size;
    &:hover {
      .button--submit:not(:hover) {
        background: transparent;
      }
    }
  }
}

.button {
  &__shortcuts {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    gap: 4px;
    height: $base-space * 2;
    border-radius: $border-radius;
    border-width: 1px 1px 3px 1px;
    border-color: $black-20;
    border-style: solid;
    box-sizing: content-box;
    color: $black-87;
    background: palette(white);
    @include font-size(11px);
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
      "Open Sans", "Helvetica Neue", sans-serif;
    padding: 0 4px;
  }
  &__shortcuts-group {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 4px;
  }
  &--submit,
  &--draft,
  &--discard {
    width: 100%;
    justify-content: center;
    color: $black-87;
    min-height: $base-space * 6;
    border-radius: $border-radius-m - 1;
    padding: $base-space;
    &:hover {
      color: $black-87;
    }
    &:disabled {
      pointer-events: visible;
      cursor: not-allowed;
      opacity: 1;
      & > * {
        opacity: 0.5;
      }
    }
  }
  &--submit {
    &:not([disabled]) {
      background: $submitted-color-light;
    }
    &:hover:not([disabled]) {
      background: darken($submitted-color-light, 2%);
    }
    &:active:not([disabled]),
    &.--button--submitting,
    &.--button--submitting:hover {
      background: $submitted-color-medium;
    }
    &.--button--remove-bg {
      background: transparent;
    }
  }
  &--draft {
    &:hover:not([disabled]) {
      background: $draft-color-light;
    }
    &:active:not([disabled]),
    &.--button--saving-draft,
    &.--button--saving-draft:hover {
      background: $draft-color-medium;
    }
  }
  &--discard {
    &:hover:not([disabled]) {
      background: $discarded-color-light;
    }
    &:active:not([disabled]),
    &.--button--discarding,
    &.--button--discarding:hover {
      background: $discarded-color-medium;
    }
  }
}

[data-title] {
  position: relative;
  overflow: visible;
  @include tooltip-mini("top");
}

@container (max-width: 500px) {
  .button {
    &--submit,
    &--draft,
    &--discard {
      flex-direction: column;
    }
  }
}
</style>
