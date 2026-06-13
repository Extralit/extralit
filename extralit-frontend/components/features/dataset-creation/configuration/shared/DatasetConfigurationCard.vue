<template>
  <div class="config-card__wrapper">
    <div class="config-card">
      <div class="config-card__content" :class="item?.type">
        <h3 class="config-card__title">
          <svgicon class="config-card__icon" width="6" name="draggable" color="var(--bg-opacity-20)" />
          <input
            v-if="isEditingName"
            ref="nameInput"
            v-model="editableName"
            class="config-card__title-input"
            @blur="finishEditing"
            @keydown.enter="finishEditing"
            @keydown.escape="cancelEditing"
          />
          <span
            v-else
            class="config-card__title-text"
            :class="{ 'config-card__title-text--editable': configType === 'question' }"
            @dblclick="configType === 'question' ? startEditing() : null"
            >{{ item.name }}</span
          >
          <span v-if="item.primitiveType" class="config-card__primitive-type">{{ item.primitiveType }}</span>
        </h3>
        <slot name="header" />
        <div class="config-card__row">
          <DatasetConfigurationChipsSelector
            :id="item.name"
            :value="item.type"
            :type="configType"
            class="config-card__type"
            :options="availableTypes"
            @onValueChange="onTypeChange($event)"
          />
        </div>
        <slot></slot>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
export default {
  props: {
    item: {
      type: Object,
      required: true,
    },
    configType: {
      type: String,
      required: true,
    },
    availableTypes: {
      type: Array,
      required: true,
    },
    removeIsAllowed: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      isEditingName: false,
      editableName: "",
    };
  },
  computed: {
    hasNoMapping() {
      return this.item.type.value === "no mapping";
    },
  },
  model: {
    prop: "type",
    event: "change",
  },
  methods: {
    onTypeChange(type) {
      // Vue 2's `v-model="item.type"` wrote the selection back locally (the only
      // mechanism for field type changes — DatasetConfigurationField does not listen
      // to change-type) AND `@onValueChange` re-emitted change-type (consumed by the
      // question form to recreate the question). Preserve both behaviours.
      this.item.type = type;
      this.$emit("change-type", type);
    },
    startEditing() {
      if (this.configType !== "question") return;
      this.isEditingName = true;
      this.editableName = this.item.name;
      this.$nextTick(() => {
        const nameInput = this.$refs.nameInput as HTMLInputElement;
        nameInput.focus();
        nameInput.select();
      });
    },
    finishEditing() {
      if (this.editableName.trim() && this.editableName !== this.item.name) {
        this.$emit("name-changed", this.editableName.trim());
      }
      this.isEditingName = false;
    },
    cancelEditing() {
      this.isEditingName = false;
      this.editableName = this.item.name;
    },
  },
};
</script>

<style lang="scss" scoped>
$validate-color: hsl(216, 55%, 54%);
$error-color: hsl(3, 100%, 69%);
$no-mapping-color: hsl(0, 0%, 50%);
.config-card {
  $this: &;
  position: relative;
  border-radius: $base-space * 2;
  border: 1px solid hsl(from var(--bg-config-card) h s 86%);
  background: var(--bg-config-card);
  transition: all 0.3s ease-in;
  &__wrapper {
    border-radius: $base-space * 2;
    background: var(--bg-accent-grey-1);
    transition: all 0.3s ease-in;
    cursor: pointer;
    &:hover {
      transition: all 0.2s ease-in;
      box-shadow: 0 0 3px 1px var(--bg-opacity-10);
      .config-card__icon {
        opacity: 1;
      }
    }
  }
  &__content {
    padding: $base-space * 2;
    display: flex;
    flex-direction: column;
    gap: $base-space;
  }
  &__title {
    display: flex;
    gap: $base-space;
    align-items: center;
    margin: 0;
    font-weight: 500;
    @include font-size(14px);
  }
  &__title-text {
    &--editable {
      cursor: pointer;
      &:hover {
        background: var(--bg-opacity-4);
        border-radius: 2px;
        padding: 1px 2px;
        margin: -1px -2px;
      }
    }
  }
  &__title-input {
    background: transparent;
    border: none;
    outline: none;
    font-family: inherit;
    font-size: inherit;
    font-weight: inherit;
    color: inherit;
    padding: 1px 2px;
    margin: -1px -2px;
    border-radius: 2px;
    background: var(--bg-accent-grey-2);
    min-width: 100px;
    &:focus {
      background: var(--bg-accent-grey-2);
      box-shadow: 0 0 0 1px var(--bg-opacity-20);
    }
  }
  &__icon {
    position: absolute;
    left: 6px;
    top: 19px;
    opacity: 0;
  }
  &__primitive-type {
    font-family: monospace, monospace;
    color: var(--fg-secondary);
    font-weight: 400;
    text-transform: lowercase;
    @include font-size(10px);
  }
  &__row {
    display: flex;
    align-items: center;
    gap: $base-space;
    width: 100%;
  }
  &__type {
    flex: 1;
  }
  :deep(.chip-selector__input + label) {
    background: hsl(from var(--bg-accent-grey-1) h s l / 60%);
    border-color: hsl(from var(--bg-config-card) h s 86%);
  }
  :deep(.chip-selector__input:checked + label) {
    background: var(--bg-accent-grey-2);
  }
  &:has(.nomapping) {
    border-color: var(--bg-opacity-10);
    background: hsl(from var(--bg-config-card) h 40% 96%);
    :deep(.chip-selector__input + label) {
      background: hsl(from var(--bg-accent-grey-1) h s l / 50%);
      border-color: var(--bg-opacity-10);
    }
    :deep(.chip-selector__input:checked + label) {
      background: var(--bg-accent-grey-2);
    }
  }
  &:has(.--error) {
    background: hsla(from $error-color h s l / 0.16);
    border-color: hsla(from $error-color h s l / 0.5);
  }
  &:deep(.switch-label) {
    @include font-size(13px);
  }
}
</style>
