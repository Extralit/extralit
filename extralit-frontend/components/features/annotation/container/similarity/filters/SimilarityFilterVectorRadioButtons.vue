<template>
  <div>
    <BaseRadioButton
      v-for="vector in vectors"
      :key="vector.id"
      :id="vector.name"
      :value="vector.name"
      v-model="selected"
    >
      {{ vector.title }}
    </BaseRadioButton>
  </div>
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
    selected() {
      this.$emit("update:modelValue", this.selected);
    },
  },
};
</script>
