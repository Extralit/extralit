<template>
  <div class="container">
    <RenderTable
      :tableJSON="question.answer.value"
      :editable="true"
      :questions="questions"
      @change-text="onChangeTextArea"
      @on-change-focus="onChangeFocus"
      @on-exit-edition-mode="onExitEditionMode"
    />
  </div>
</template>

<script>

export default {
  name: "TableComponent",
  props: {
    question: {
      type: Object,
      required: true,
    },
    questions: {
      type: Array,
      required: true,
    },
  },
  methods: {
    onChangeTextArea(newText) {
      this.question.answer.value = newText;
    },
    onChangeFocus(isFocus) {
      if (isFocus) {
        this.$emit("on-focus");
      }
    },
    onExitEditionMode() {
      this.$refs.container.focus({
        preventScroll: true,
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.container {
  display: flex;
  flex-direction: column;
  gap: $base-space;
}
</style>
