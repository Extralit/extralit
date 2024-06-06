<template>
  <div class="text_field_component" :key="fieldText">
    <div class="title-area --body2">
      <span class="text_field_component__title-content" v-text="title" />
      <BaseActionTooltip
        class="text_field_component__tooltip"
        tooltip="Copied"
        tooltip-position="left"
      >
        <BaseButton
          title="Copy to clipboard"
          class="text_field_component__copy-button"
          @click.prevent="$copyToClipboard(fieldText)"
        >
          <svgicon color="#acacac" name="copy" width="20" height="20" />
        </BaseButton>
      </BaseActionTooltip>
    </div>
    <div id="`fields-content-${name}`" class="content-area --body1">
      <RenderTableBaseComponent v-if="useTable && isValidTableJSON" :tableData="fieldText" />
      <RenderHTMLBaseComponent 
        v-else-if="isValidHTML" 
        style="display: block; white-space: pre-wrap; max-width: 100%; overflow-x: auto !important;" 
        :value="fieldText" 
        :editable="false" />
      <RenderMarkdownBaseComponent v-else-if="useMarkdown" :markdown="fieldText" />
      <div :class="classes" v-else v-html="fieldText" />
      <template>
        <style :key="name" scoped>
          ::highlight(search-text-highlight-{{name}}) {
            color: #ff675f;
          }
        </style>
      </template>
    </div>
  </div>
</template>

<script>
import { useTextFieldViewModel } from "./useTextFieldViewModel";
import { isTableJSON } from "@/components/base/base-render-table/tableUtils";
export default {
  name: "TextFieldComponent",
  props: {
    name: {
      type: String,
      required: true,
    },
    title: {
      type: String,
      required: true,
    },
    searchText: {
      type: String,
      default: "",
    },
    fieldText: {
      type: String,
      required: true,
    },
    useMarkdown: {
      type: Boolean,
      default: false,
    },
    useTable: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    isValidTableJSON() {
      return isTableJSON(this.text);
    },
    isValidHTML() {
      const value = this.text?.trimStart();
      return value?.startsWith("<table") && !value?.startsWith("<img") && !value?.startsWith("<iframe");
    },
    classes() {
      return this.$language.isRTL(this.fieldText) ? "--rtl" : "--ltr";
    },
  },
  setup(props) {
    return useTextFieldViewModel(props);
  },
};
</script>

<style lang="scss" scoped>
.text_field_component {
  $this: &;
  display: flex;
  flex-direction: column;
  gap: $base-space;
  padding: 2 * $base-space;
  background: palette(grey, 800);
  border-radius: $border-radius-m;
  &:hover {
    #{$this}__copy-button {
      opacity: 1;
    }
  }
  .title-area {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: $base-space;
    color: $black-87;
  }
  .content-area {
    white-space: pre-wrap;
    word-break: break-word;
  }
  &__title-content {
    word-break: break-word;
    padding-bottom: 10px;
    border-bottom: 1px solid #333;
    font-size: 16px;
    font-weight: 500;
    width: calc(100% - 30px);
  }
  &__tooltip {
    display: flex;
    align-self: flex-start;
    z-index: 1;
  }
  &__copy-button {
    flex-shrink: 0;
    padding: 0;
    opacity: 0;
  }
}
.fade-enter-active,
.fade-leave-active {
  transition: all 0.25s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
