<template>
  <div class="container">
    <RenderTableBaseComponent
      v-if="question.settings.settings.use_table && isValidTableJSON"
      class="textarea"
      :tableData="question.suggestion?.suggestedAnswer"
      :editable="true"
      @onUpdateAnswer="onUpdateAnswer"
    />
    <RenderHTMLBaseComponent
      v-else-if="question.settings.settings.use_table && isValidHTML"
      class="textarea"
      :value="question.suggestion?.suggestedAnswer"
    />
    <MarkdownRenderer
      v-else
      class="textarea--markdown"
      :markdown="question.suggestion?.value"
    />
    <BaseActionTooltip :tooltip="$t('copied')" class="button-copy">
      <BaseButton @on-click="$copyToClipboard(question.suggestion?.value)">
        <svgicon name="copy" width="16" height="16" />
      </BaseButton>
    </BaseActionTooltip>
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
  methods: {
    onUpdateAnswer(tableJsonString) {
      this.question.answer.value = tableJsonString;
    },
  }

};
</script>

<style lang="scss" scoped>
.container {
  position: relative;
  display: flex;
  padding: $base-space * 2;
  border: 1px solid var(--bg-opacity-20);
  border-radius: $border-radius-s;
  background: var(--bg-accent-grey-2);
  min-height: 5em;
  &:hover {
    .button-copy {
      display: block;
    }
  }
}
.button-copy {
  display: none;
  position: absolute;
  right: $base-space;
  top: $base-space;
  .button {
    padding: 0;
  }
  .svg-icon {
    color: var(--fg-tertiary);
  }
}
</style>
