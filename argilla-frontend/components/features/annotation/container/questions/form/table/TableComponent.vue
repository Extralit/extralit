<template>
  <div class="table-component">
    <RenderTable
      :tableJSON="question.answer.value"
      :editable="true"
      @change-text="onChangeTextArea"
      @on-change-focus="onChangeFocus"
      @on-exit-edition-mode="onExitEditionMode"
    />
  </div>
</template>

<script>
import RenderTable from "@/components/base/base-render-table/RenderTable";

export default {
  name: "TableComponent",
  components: {
    RenderTable,
  },
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

<style scoped>
.table-component {
  display: flex;
  flex-direction: column;
  gap: $base-space;
}
</style>
