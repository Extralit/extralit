<template>
  <SimilarityConfigDropdown
    v-if="selected && vectors.length > 1"
    v-model="selected"
    :options="vectors"
    :useExtraText="$t('with')"
    :useTextCapitalized="false"
    useTextProp="title"
    useKeyProp="name"
  />
</template>
<script>
export default {
  props: {
    modelValue: {
      type: String,
    },
    vectors: {
      type: Array,
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
