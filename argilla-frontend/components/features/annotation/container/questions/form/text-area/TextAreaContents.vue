<template>
  <div
    class="container"
    ref="container"
    :class="classes"
    @focus="onFocus"
    :tabindex="isEditionModeActive ? '-1' : '0'"
    @keydown.shift.enter.exact.prevent="onEditMode"
  >
    <RenderHTMLBaseComponent
      v-if="question.settings.use_markdown && isValidHTML"
      class="textarea"
      :value="question.answer.value"
      :editable="true"
      :originalValue="question.answer.originalValue"
      :placeholder="placeholder"
      :isFocused="isEditionModeActive"
      @change-text="onChangeTextArea"
      @on-change-focus="onChangeFocus"
      @on-exit-edition-mode="onExitEditionMode"
    />
    <RenderTableBaseComponent
      v-else-if="question.settings.use_table && isValidTableJSON"
      class="textarea"
      :tableData="question.answer.value"
      :editable="true"
      :questions="questions"
      @change-text="onChangeTextArea"
      @on-change-focus="onChangeFocus"
      @on-exit-edition-mode="onExitEditionMode"
    />
    <MarkdownRenderer
      v-else-if="question.settings.use_markdown && !isEditionModeActive"
      class="textarea--markdown"
      :markdown="question.answer.value"
      @click.native="onFocus"
    />
    <ContentEditableFeedbackTask
      v-else
      class="textarea"
      :value="question.answer.value"
      :originalValue="question.answer.originalValue"
      :placeholder="placeholder"
      :isFocused="isEditionModeActive"
      @change-text="onChangeTextArea"
      @on-change-focus="onChangeFocus"
      @on-exit-edition-mode="onExitEditionMode"
      role="textbox"
    />
  </div>
</template>

<script>
import { isTableJSON } from "@/components/base/base-render-table/tableUtils";

export default {
  name: "TextAreaComponent",
  props: {
    question: {
      type: Object,
      required: true,
    },
    questions: {
      type: Array,
      required: true,
    },
    isFocused: {
      type: Boolean,
      default: () => false,
    },
  },
  data: () => {
    return {
      isEditionModeActive: false,
      isExitedFromEditionModeWithKeyboard: false,
    };
  },
  watch: {
    isFocused: {
      immediate: true,
      handler(newValue) {
        if (this.question.isRequired && !this.question.isAnswered) {
          this.onChangeFocus(newValue);

          return;
        }

        if (newValue) {
          this.$nextTick(() => {
            this.onExitEditionMode();
          });
        }
      },
    },
  },
  methods: {
    onEditMode() {
      if (this.isExitedFromEditionModeWithKeyboard) {
        this.isEditionModeActive = true;
      }
    },
    onExitEditionMode() {
      this.$refs.container.focus({
        preventScroll: true,
      });
      this.isEditionModeActive = false;
      this.isExitedFromEditionModeWithKeyboard = true;
    },
    onChangeTextArea(newText) {
      const isAnyText = newText?.length;

      this.question.answer.value = isAnyText ? newText : "";

      if (this.question.isRequired) {
        this.$emit("on-error", !isAnyText);
      }
    },
    onChangeFocus(isFocus) {
      this.isEditionModeActive = isFocus;

      if (isFocus) {
        this.$emit("on-focus");
      }
    },
    onFocus(event) {
      if (event.defaultPrevented) return;
      if (this.question.settings.use_table) {
        this.$emit("on-focus");
      }

      this.isEditionModeActive = true;
      this.isExitedFromEditionModeWithKeyboard = false;
    },
    onUpdateAnswer(tableJsonString) {
      this.question.answer.value = tableJsonString;
    },
  },
  computed: {
    classes() {
      if (this.question.settings.use_table && (this.isValidHTML || this.isValidTableJSON)) {
        return "--table";
      } else if (this.isEditionModeActive) {
        return "--editing";
      }

      return null;
    },
    isValidTableJSON() {
      return isTableJSON(this.question.answer.value);
    },
    isValidHTML() {
      const value = this.question.answer?.value?.trimStart();

      return value?.startsWith("<") && !value?.startsWith("<img") && !value?.startsWith("<iframe");
    },
    placeholder() {
      if (this.question.settings.use_table) {
        return this.$t("table_form_placeholder");
      }
      return this.question.settings.placeholder;
    }
  },
};
</script>

<style lang="scss" scoped>
.container {
  display: flex;
  min-height: 4em;
  padding: $base-space;
  border: 1px solid var(--bg-opacity-20);
  border-radius: $border-radius-s;
  background: var(--bg-accent-grey-2);
  outline: none;
  &.--table {
    border: none;
    padding: 0;
  }
  &.--editing {
    border-color: var(--fg-cuaternary);
    outline: 1px solid var(--fg-cuaternary);
  }
  &:focus {
    outline: 1px solid var(--bg-opacity-20);
  }
  &:focus:not(:focus-visible) {
    outline: none;
  }
  .content--exploration-mode & {
    border: none;
    padding: 0;
  }
}

.textarea {
  display: flex;
  flex: 0 0 100%;
  &--markdown {
    display: inline;
    flex: 1;
    padding: 0px;
  }
}
</style>
