<template>
  <div
    class="container"
    ref="container"
    :class="classes"
    @focus="onFocus"
    :tabindex="isEditionModeActive ? '-1' : '0'"
    @keydown.shift.enter.exact.prevent="onEditMode"
  >
    <RenderTableBaseComponent
      v-if="question.settings.use_table && isValidTableJSON"
      class="textarea"
      :tableData="question.answer.value"
      :editable="true"
      @click.native="onFocus"
      @on-change-focus="onChangeFocus"
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
      :placeholder="question.settings.placeholder"
      :isFocused="isEditionModeActive"
      @change-text="onChangeTextArea"
      @on-change-focus="onChangeFocus"
      @on-exit-edition-mode="onExitEditionMode"
    />
  </div>
</template>

<script>
import { isTableJSON } from "@/components/base/base-render-table/tableUtils.js";

export default {
  name: "TextAreaComponent",
  props: {
    question: {
      type: Object,
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
  },
  computed: {
    classes() {
      if (this.question.settings.use_table && this.isValidTableJSON) {
        // This first clause prevents the table from having --table or --editing class
        return "--table";
      } else if (this.isEditionModeActive) {
        return "--editing";
      }

      return null;
    },
    isValidTableJSON() {
      return isTableJSON(this.question.answer.value);
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
.container {
  display: flex;
  padding: $base-space;
  border: 1px solid $black-20;
  border-radius: $border-radius-s;
  min-height: 10em;
  background: palette(white);
  outline: none;
  &.--table {
    border: none;
    padding: 0;
  }
  &.--editing {
    border-color: $primary-color;
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
