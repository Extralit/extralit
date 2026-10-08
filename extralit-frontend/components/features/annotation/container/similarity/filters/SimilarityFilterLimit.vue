<template>
  <SimilarityConfigDropdown
    :data-title="$t('similarity.record-number')"
    v-model="selected"
    :options="[10, 50, 100, 200]"
  />
</template>
<script>
export default {
  props: {
    modelValue: {
      type: Number,
      required: true,
    },
  },
  emits: ["update:modelValue"],
  data() {
    return {
      selected: this.modelValue,
    };
  },
  watch: {
    modelValue(newValue) {
      this.selected = newValue;
    },
    selected() {
      this.$emit("update:modelValue", this.selected);
    },
  },
};
</script>

<style lang="scss" scoped>
[data-title] {
  position: relative;
  overflow: visible;
  @include tooltip-mini("top");
  &:after {
    right: 0;
  }
}
</style>
