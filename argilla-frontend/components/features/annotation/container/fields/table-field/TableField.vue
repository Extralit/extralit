<template>
  <div class="table_field_component">
    <div class="title-area --body2">
      <span class="table_field_component__title-content" v-text="title" />
      <BaseActionTooltip
        class="table_field_component__tooltip"
        :tooltip="$t('copied')"
        tooltip-position="left"
      >
        <BaseButton
          :title="$t('button.tooltip.copyToClipboard')"
          class="table_field_component__copy-button"
          @click.prevent="$copyToClipboard(JSON.stringify(content))"
        >
          <svgicon color="#acacac" name="copy" width="18" height="18" />
        </BaseButton>
      </BaseActionTooltip>
    </div>
    <RenderTable
      :tableJSON="content"
      :editable="false"
    />
  </div>
</template>

<script lang="ts">

export default {
  name: 'TableField',
  props: {
    name: {
      type: String,
      required: true,
    },
    title: {
      type: String,
    },
    content: {
      type: [Object, String],
      required: true,
    },
  },
};
</script>

<style lang="scss" scoped>
.table_field_component {
  $this: &;
  display: flex;
  flex-direction: column;
  gap: $base-space;
  padding: 2 * $base-space;
  background: var(--bg-field);
  border-radius: $border-radius-m;
  border: 1px solid var(--border-field);

  &__title-content {
    word-break: break-word;
    width: calc(100% - 30px);
    color: var(--fg-secondary);
  }

  &:hover {
    #{$this}__copy-button {
      opacity: 1;
    }
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

  .title-area {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: $base-space;
    color: var(--fg-primary);
  }
}
</style>