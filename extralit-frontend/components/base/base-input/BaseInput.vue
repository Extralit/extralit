<template>
  <input
    ref="input"
    class="input"
    :type="type"
    :name="name"
    :value="value"
    :disabled="disabled"
    :required="required"
    :placeholder="placeholder"
    :maxlength="maxlength"
    :readonly="readonly"
    @focus="onFocus"
    @blur="onBlur"
    @input="onInput"
    @keydown.up="onInput"
    @keydown.down="onInput"
  />
</template>

<script>
import common from "./common";
import getClosestVueParent from "./utils/getClosestVueParent";

export default {
  mixins: [common],
  props: {
    type: {
      type: String,
      default: "text",
    },
    autofocus: {
      type: Boolean,
      default: false,
    },
  },
  watch: {
    autofocus: {
      immediate: true,
      handler() {
        this.$nextTick(() => {
          if (this.autofocus) {
            this.$refs.input.focus();
          }
        });
      },
    },
  },
  mounted() {
    this.$nextTick(() => {
      this.parentContainer = getClosestVueParent(this.$parent, "input-container");

      if (!this.parentContainer) {
        this.$destroy();

        throw new Error("You should wrap the input in a input-container");
      }

      this.parentContainer.inputInstance = this;
      this.setParentDisabled();
      this.setParentRequired();
      this.setParentPlaceholder();
      this.handleMaxLength();
      this.updateValues();
    });
  },
};
</script>
