<template>
  <div class="container">
    <div class="inputs-area" role="radiogroup" aria-label="Label-Options">
      <div
        v-for="option in modelValue"
        :key="option.id"
        class="input-button"
        role="button"
        :aria-label="option.text"
        @keydown.enter.prevent
      >
        <BaseTooltip
          :title="isSuggested(option) ? $t('suggestion.name') : ''"
          :text="getSuggestedInfo(option)"
          minimalist
        >
          <input
            :id="option.id"
            ref="options"
            v-model="option.isSelected"
            type="checkbox"
            :name="option.value"
            @change="onSelect(option)"
            @focus="onFocus"
          />
          <label
            class="label-text"
            :class="{
              'label-active': option.isSelected,
            }"
            :for="option.id"
          >
            {{ option.value }}

            <svgicon v-if="isSuggested(option)" class="label-text__suggestion-icon" name="suggestion" />
          </label>
        </BaseTooltip>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "RatingMonoSelectionComponent",
  props: {
    modelValue: {
      type: Array,
      required: true,
    },
    isFocused: {
      type: Boolean,
      default: () => false,
    },
    suggestion: {
      type: Object,
    },
  },
  // v-model consumer (rating/Rating.component.vue): same Vue 3 migration as
  // LabelSelection — rename `options` → `modelValue` and emit `update:modelValue`.
  emits: ["update:modelValue", "on-focus", "on-selected"],
  watch: {
    isFocused: {
      immediate: true,
      handler(newValue) {
        if (newValue) {
          this.$nextTick(() => {
            const options = this.$refs?.options;
            if (options.some((o) => o.contains(document.activeElement))) {
              return;
            }
            options[0].focus();
          });
        }
      },
    },
  },
  methods: {
    isSuggested(option) {
      return this.suggestion?.isSuggested(option.value);
    },
    getSuggestedInfo(option) {
      const suggestion = this.suggestion?.getSuggestion(option.value);
      if (!suggestion) return;

      const agent = suggestion.agent ? `${suggestion.agent}: ` : "";
      const score = suggestion.score?.fixed ?? "";

      return `${agent}${score}`;
    },
    onSelect({ id, isSelected }) {
      this.modelValue.forEach((option) => {
        option.isSelected = option.id === id ? isSelected : false;
      });

      this.$emit("update:modelValue", this.modelValue);

      if (isSelected) {
        this.$emit("on-selected");
      }
    },
    onFocus() {
      this.$emit("on-focus");
    },
  },
};
</script>

<style lang="scss" scoped>
.container {
  display: flex;
  .inputs-area {
    display: inline-flex;
    gap: $base-space;
    border-radius: $border-radius-rounded;
  }
}
.label-text {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  border-radius: $border-radius-rounded;
  height: $base-space * 4;
  min-width: $base-space * 4;
  padding-inline: $base-space;
  outline: none;
  background: var(--bg-label-unselected);
  border: 1px solid var(--bg-opacity-1);
  color: var(--fg-label);
  font-weight: 500;
  overflow: hidden;
  transition: all 0.2s ease-in-out;
  cursor: pointer;

  &__suggestion-icon {
    flex-shrink: 0;
    width: 10px;
    height: 10px;
  }

  &.label-active {
    color: var(--color-white);
    background: var(--bg-label);
    box-shadow: none;
    @media (forced-colors: active) {
      outline: 5px solid;
    }
    &:hover {
      box-shadow: inset 0 -2px 6px 0 hsl(from var(--bg-label) h s l / 80%);
      background: hsl(from var(--bg-label) h s l / 80%);
    }
  }

  &:not(.label-active):hover {
    background: var(--bg-label-unselected-hover);
    transition: all 0.2s ease-in-out;
  }
}
input[type="checkbox"] {
  @extend %visuallyhidden;
  &:focus {
    & + .label-text {
      outline: 2px solid var(--fg-cuaternary);
    }
  }
}
.input-button:not(:first-of-type) {
  input[type="checkbox"] {
    &:focus:not(:focus-visible) {
      & + .label-text {
        outline: none;
        &.label-active {
          outline: none;
        }
      }
    }
  }
}

[data-title] {
  position: relative;
  overflow: visible;
  @include tooltip-mini("top");
}
</style>
