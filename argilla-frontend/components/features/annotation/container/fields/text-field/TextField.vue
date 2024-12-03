<template>
  <div class="text_field_component" :key="fieldText">
    <div class="title-area --body2">
      <span class="text_field_component__title-content" v-text="title" />
      <BaseActionTooltip
        class="text_field_component__tooltip"
        :tooltip="$t('copied')"
        tooltip-position="left"
      >
        <BaseButton
          :title="$t('button.tooltip.copyToClipboard')"
          class="text_field_component__copy-button"
          @click.prevent="$copyToClipboard(fieldText)"
        >
          <svgicon color="#acacac" name="copy" width="18" height="18" />
        </BaseButton>
      </BaseActionTooltip>
    </div>
    <div :id="`fields-content-${id}`" class="content-area --body1">
      <RenderTable v-if="useTable && isValidTableJSON" :tableJSON="JSON.parse(fieldText)" />
      <MarkdownRenderer v-else-if="useMarkdown" :markdown="fieldText" />
      <Sandbox v-else-if="isHTML" :content="fieldText" />
      <div :class="classes" v-else v-html="fieldText" />
      <template>
        <style :key="id" scoped>
          ::highlight(search-text-highlight-{{id}}) {
            color: #ff675f;
          }
        </style>
      </template>
    </div>
  </div>
</template>

<script>
import { useTextFieldViewModel } from "./useTextFieldViewModel";
import { isValidJSON } from "@/components/base/base-render-table/tableUtils";
export default {
  props: {
    id: {
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
    record: {
      type: Object,
    },
    useTable: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    isValidTableJSON() {
      return isValidJSON(this.fieldText);
    },
    classes() {
      return this.$language.isRTL(this.fieldText) ? "--rtl" : "--ltr";
    },
    isHTML() {
      return /<([A-Za-z][A-Za-z0-9]*)\b[^>]*>(.*?)<\/\1>/.test(this.fieldText);
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
  background: var(--bg-field);
  border-radius: $border-radius-m;
  border: 1px solid var(--border-field);
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
    color: var(--fg-primary);
  }
  .content-area {
    white-space: pre-wrap;
    word-break: break-word;
  }
  &__title-content {
    word-break: break-word;
    // padding-bottom: 10px;
    // border-bottom: 1px solid #333;
    // font-size: 16px;
    // font-weight: 500;
    width: calc(100% - 30px);
    color: var(--fg-secondary);
  }
  &__tooltip {
    display: flex;
    align-self: flex-start;
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
