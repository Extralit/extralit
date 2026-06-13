<template>
  <SimilarityConfigDropdown v-model="selected" :options="['most', 'least']" />
</template>
<script>
export default {
  props: {
    modelValue: {
      type: String,
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
