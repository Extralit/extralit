<template>
  <div class="container">
    <BaseActionTooltip tooltip="Copied" class="button-copy">
      <BaseButton
        @on-click="$copyToClipboard(question.suggestion?.suggestedAnswer)"
      >
        <svgicon name="copy" width="16" height="16" />
      </BaseButton>
    </BaseActionTooltip>
    <RenderTableBaseComponent
      v-if="question.settings.use_table && isValidTableJSON"
      class="textarea"
      :editable="true"
      :tableData="question.suggestion?.suggestedAnswer"
    />
    <RenderHTMLBaseComponent
      v-else-if="question.settings.use_table && isValidHTML"
      class="textarea"
      :value="question.suggestion?.suggestedAnswer"
    />
    <RenderMarkdownBaseComponent
      v-else
      class="textarea--markdown"
      :markdown="question.suggestion?.suggestedAnswer"
    />
  </div>
</template>

<script>
import "assets/icons/copy";
import { isTableJSON } from "@/components/base/base-render-table/tableUtils";

export default {
  name: "TextAreaComponent",
  props: {
    question: {
      type: Object,
      required: true,
    },
  },
  computed: {
    isValidHTML() {
      const value = this.question.suggestion?.suggestedAnswer?.trimStart();

      return value?.startsWith("<") && !value?.startsWith("<img") && !value?.startsWith("<iframe");
    },
    isValidTableJSON() {
      return isTableJSON(this.question.suggestion?.suggestedAnswer);
    },
  },
};
</script>

<style lang="scss" scoped>
.container {
  position: relative;
  display: flex;
  padding: $base-space * 2;
  border: 1px solid $black-20;
  border-radius: $border-radius-s;
  min-height: 10em;
  background: palette(white);
  &:hover {
    .button-copy {
      display: block;
    }
  }
}
.button-copy {
  display: none;
  position: absolute;
  right: $base-space * 2;
  top: $base-space * 2;
  .button {
    padding: 0;
  }
  .svg-icon {
    color: $black-37;
  }
}
</style>
