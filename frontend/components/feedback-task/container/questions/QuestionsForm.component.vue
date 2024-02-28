<template>
  <form
    class="questions-form"
    :class="questionFormClass"
    @submit.prevent="onSubmit"
    v-click-outside="onClickOutside"
    @click="focusOnFirstQuestionFromOutside"
  >
    <div class="questions-form__content">
      <div class="questions-form__header">
        <div class="draft">
          <p v-if="draftSaving">
            <svgicon color="#0000005e" name="refresh" />
            {{ $t("saving") }}
          </p>
          <p v-else-if="record.isDraft">
            {{ $t("saved") }}
            <BaseDate
              class="tooltip"
              :date="record.updatedAt"
              format="date-relative-now"
              :updateEverySecond="10"
            />
          </p>
        </div>
        <p class="questions-form__guidelines-link">
          Read the
          <NuxtLink
            :to="{
              name: 'dataset-id-settings',
              params: { id: datasetId },
            }"
            target="_blank"
            >annotation guidelines <svgicon name="external-link" width="12" />
          </NuxtLink>
        </p>
      </div>

      <QuestionsComponent
        :questions="record.questions"
        :autofocusPosition="autofocusPosition"
        @on-focus="updateQuestionAutofocus"
      />
    </div>
    <div class="footer-form">
      <div class="footer-form__left-footer">
        <BaseButton
          type="button"
          class="primary text"
          @click.prevent="onClear"
          :title="$t('shortcuts.questions_form.clear')"
        >
          <span v-text="'Clear'" />
        </BaseButton>
      </div>
      <div class="footer-form__right-area">
        <BaseButton
                    type="button"
          class="primary outline"
          @on-click="onDiscard"
        :disabled="record.isDiscarded"
          :title="$t('shortcuts.questions_form.discard')"
        >
          <span v-text="'Discard'" />
        </BaseButton>
        <BaseButton
          type="submit"
          class="primary"
          :disabled="isSubmitButtonDisabled"
          :title="$t('shortcuts.questions_form.submit')"
        >
          <span v-text="'Submit'" />
        </BaseButton>
      </div>
    </div>
  </form>
</template>

<script>
import "assets/icons/external-link";
import "assets/icons/refresh";
import interact from 'interactjs'

import { useQuestionFormViewModel } from "./useQuestionsFormViewModel";

export default {
  name: "QuestionsFormComponent",

  props: {
    datasetId: {
      type: String,
      required: true,
    },
    record: {
      type: Object,
      required: true,
    },
  },

  data() {
    return {
      autofocusPosition: 0,
      interactionCount: 0,
      isTouched: false,
      userComesFromOutside: false,
      timer: null,
      duration: 0,
    };
  },

  setup() {
    return useQuestionFormViewModel();
  },

  computed: {
    questionFormClass() {
      if (this.isSubmitting) return "--submitted --waiting";
      if (this.isDiscarding) return "--discarded --waiting";
      
      if (this.isTouched || (this.formHasFocus && this.interactionCount > 1))
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
    isSubmitButtonDisabled() {
    if (this.record.isSubmitted)
        return !this.isTouched || !this.questionAreCompletedCorrectly;

      return !this.questionAreCompletedCorrectly;
    },
  },

  watch: {
    record: {
      deep: true,
      immediate: true,
      handler() {
        if (this.record.isModified) this.saveDraft(this.record);

        this.isTouched = this.record.isSubmitted && this.record.isModified;
      },
    },
  },

  mounted() {
    document.addEventListener("keydown", this.handleGlobalKeys);
    interact(this.$el)
      .resizable({
        edges: { left: true, right: false, bottom: false, top: false },
      })
      .on('resizemove', event => {
        let target = event.target;
        let newWidth = event.rect.width;
        let clampedWidth = Math.max(Math.min(newWidth, 0.8 * target.parentElement.offsetWidth), 0.4 * target.parentElement.offsetWidth);
        target.style.flexBasis = clampedWidth + 'px';
      });
      
    // Listen for visibility change events
    this.startTimer();
    document.addEventListener('visibilitychange', this.handleVisibilityChange);
  },

  beforeDestroy() {
    this.stopTimer();
    document.removeEventListener('visibilitychange', this.handleVisibilityChange);
  },

  destroyed() {
    document.removeEventListener("keydown", this.handleGlobalKeys);
  },

  methods: {
    focusOnFirstQuestionFromOutside(event) {
      // Prevents jumping around when the user clicks on a button or interacting with the table
      return
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
      return
      const { code, ctrlKey, metaKey, shiftKey } = event;

      if (shiftKey) return;

      if (code === "Tab" && this.userComesFromOutside) {
        this.focusOnFirstQuestion(event);

        return;
      }

      switch (code) {
        case "KeyS": {
          if (this.$platform.isMac) {
            if (!metaKey) return;
          } else if (!ctrlKey) return;
          event.preventDefault();
          event.stopPropagation();
          this.onSaveDraftImmediately();
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
          break;
        }
      }
    },
    async onDiscard() {
      if (this.record.isDiscarded) return;

      await this.discard(this.record);

      this.$emit("on-discard-responses");
    },
    async onSubmit() {
      if (this.isSubmitButtonDisabled) return;

      let durationWrapper = { value: this.duration };
      await this.submit(this.record, durationWrapper);
      this.duration = durationWrapper.value; 

      this.$emit("on-submit-responses");
    },
    async onClear() {
      await this.clear(this.record);
    },
    async onSaveDraftImmediately() {
      let durationWrapper = { value: this.duration };
      await this.saveDraftImmediately(this.record, durationWrapper);
      this.duration = durationWrapper.value;
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
        this.duration++;
      }, 1000);
    },
    stopTimer() {
      clearInterval(this.timer);
      this.timer = null;
    },
    resetTimer() {
      this.duration = 0;
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
  flex-basis: clamp(40%, 30vw, 80%);
  // @include media(">desktopLarge") {
  //   max-width: clamp(40%, 45vw, 80%);
  // }
  max-height: 100%;
  min-width: 0;
  justify-content: space-between;
border-radius: $border-radius-m;
  border: 1px solid transparent;
  background: palette(white);
  margin-bottom: auto;
  &__header {
    align-items: baseline;
  }
  &__title {
    margin: 0 0 calc($base-space / 2) 0;
    color: $black-87;
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
        text-decoration: underline;
      }
    }
  }
  &__content {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: $base-space * 4;
    padding: $base-space * 3;
    overflow: auto;
    scroll-behavior: smooth;
    }

  &.--pending,
  &.--draft {
      border-color: $black-10;
    }
    &.--discarded {
      border-color: $discarded-color;
    }
    &.--submitted {
      border-color: $submitted-color;
    }
    &.--focused-form {
      border-color: palette(brown);
    }
    &.--waiting .questions-form__content {
      opacity: 0.7;
  }
}

.footer-form {
      display: flex;
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
    padding: $base-space * 2 $base-space * 3;
  border-top: 1px solid $black-10;
  &__left-area {
    display: inline-flex;
    }
  &__right-area {
    display: inline-flex;
    gap: $base-space * 2;
  }
}

.draft {
  position: absolute;
  right: $base-space * 2;
  top: $base-space;
  user-select: none;
  display: flex;
  flex-direction: row;
  gap: 5px;
  align-items: center;
  margin: 0;
  @include font-size(12px);
  color: $black-37;
  font-weight: 500;
  p {
    margin: 0;
    &:hover {
      .tooltip {
        opacity: 1;
        height: auto;
        width: auto;
        overflow: visible;
      }
    }
  }
  .tooltip {
    opacity: 0;
    height: auto;
    width: 0;
    @extend %tooltip;
    top: 50%;
    transform: translateY(-50%);
    right: calc(100% + 10px);
    overflow: hidden;
    &:before {
      position: absolute;
      @extend %triangle-right;
      left: 100%;
    }
  }
}
</style>
