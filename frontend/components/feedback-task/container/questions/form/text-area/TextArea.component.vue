<template>
  <div class="wrapper">
    <QuestionHeaderComponent
      :question="question"
      :showSuggestion="showSuggestion"
    />
    <div
      class="container"
      ref="container"
      :class="classes"
      @focus="onFocus"
      :tabindex="isEditionModeActive ? '-1' : '0'"
      @keydown.enter.exact.prevent="onEditMode"
    >
      <RenderTableBaseComponent
        v-if="question.settings.use_table && isValueJSON"
        class="textarea"
        :tableData="question.answer.value"
        :editable="true"
        v-model="question.answer.hasValidValues"
      />
      <RenderMarkdownBaseComponent
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
        :placeholder="inputPlaceholder"
        :isFocused="isFocused"
        :isEditionModeActive="isEditionModeActive"
        @change-text="onChangeTextArea"
        @on-change-focus="onChangeFocus"
        @on-exit-edition-mode="onExitEditionMode"
      />
    </div>
  </div>
</template>

<script>
export default {
  name: "TextAreaComponent",
  props: {
    question: {
      type: Object,
      required: true,
    },
    showSuggestion: {
      type: Boolean,
      default: () => false,
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
        this.isEditionModeActive = newValue;
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
      this.$refs.container.focus();
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

      this.isEditionModeActive = true;
      this.isExitedFromEditionModeWithKeyboard = false;
    },
  },
  computed: {
    classes() {
      if (this.question.settings.use_table && this.isValueJSON) {
        // This first clause prevents the table from having --table or --editing class
        return "--table";
      } else if (this.isEditionModeActive) {
        return "--editing";
      } else if (this.isFocused && this.isExitedFromEditionModeWithKeyboard) {
        return "--focus";
      }
      
      return null;
    },
    inputPlaceholder() {
      if (this.question.settings.use_table) {
        return "If corrections are needed, copy and paste the table from left-hand side to edit the data. \n" +
          "If the extracted data is irredeemable, describe what's wrong, otherwise leave blank to indicate correct extraction.";
      } else if (this.question.settings?.placeholder !== null) {
        return this.question.settings.placeholder;
      }
      return null;
    },
    isValueJSON() {
      const value = this.question.answer.value;
      if (!value?.length || !value.startsWith('{')) { return false; }

      try {
        JSON.parse(value);
      } catch (e) {
        return false;
      }
      return true;
    },
  },
  mounted() {
    this.$nuxt.$on('on-update-response-tabledata', (tableJsonString) => {
      if (this.question.settings.use_table) {
        this.question.answer.value = tableJsonString;
      }
    });
  },
  destroyed() {
    this.$nuxt.$off('on-update-response-tabledata');
  },
};
</script>

<style lang="scss" scoped>
.wrapper {
  display: flex;
  flex-direction: column;
  gap: $base-space;
}

.container {
  display: flex;
  padding: $base-space;
  border: 1px solid $black-20;
  border-radius: $border-radius-s;
  min-height: 10em;
  background: palette(white);
  &.--editing {
    border-color: $primary-color;
  }
  &.--focus {
    outline: 2px solid $primary-color;
  }
  &.--table {
    padding: 0px;
    border: 0px;
    min-height: none;
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
