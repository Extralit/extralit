<template>
  <div class="wrapper">
    <QuestionHeaderComponent :question="question" />
    <TextAreaContents
      v-if="!question.suggestion"
      :question="question"
      :questions="questions"
      :is-focused="isFocused"
    />
    <BaseCardWithTabs v-else :tabs="tabs" tabSize="small">
      <template v-slot="{ currentComponent }">
        <component
          :question="question"
          :questions="questions"
          :is-focused="isFocused"
          :is="currentComponent"
          :key="currentComponent"
        />
      </template>
    </BaseCardWithTabs>
  </div>
</template>

<script>
export default {
  name: "TextAreaComponent",
  props: {
    question: {
      type: Object,
      required: true,
    },
    questions: {
      type: Array,
      required: true,
    },
    isFocused: {
      type: Boolean,
      default: () => false,
    },
  },
  computed: {
    isSuggested() {
      return this.question.suggestion?.isSuggested(this.question.answer.value);
    },
    suggestedScore() {
      return this.question.suggestion?.score?.toFixed(1);
    },
    suggestedAgent() {
      return this.question.suggestion?.agent;
    },
    tabs() {
      return [
        {
          id: "0",
          name: this.isSuggested ? `Use: ${this.suggestedAgent}` : this.$nuxt.$t("questions_form.write"),
          icon: this.isSuggested ? "suggestion" : "",
          info: this.isSuggested ? this.suggestedScore : "",
          tooltipTitle: this.isSuggested
            ? this.$nuxt.$t("suggestion.name")
            : "",
          tooltipText: this.isSuggested ? this.suggestedAgent : "",
          component: "TextAreaContents",
        },
        ...(!this.isSuggested
          ? [
              {
                id: "1",
                name: `${this.suggestedAgent}`,
                icon: "suggestion",
                info: this.suggestedScore,
                tooltipTitle: this.$nuxt.$t("suggestion.name"),
                tooltipText: this.suggestedAgent,
                component: "TextAreaSuggestion",
              },
            ]
          : []),
      ];
    },
  },
};
</script>

<style lang="scss" scoped>
.wrapper {
  display: flex;
  flex-direction: column;
  gap: $base-space;
}
</style>
