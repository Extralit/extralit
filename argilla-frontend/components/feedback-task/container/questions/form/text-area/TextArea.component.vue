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
    suggestionAgent() {
      return this.question.suggestion?.agent || 'Suggestion';
    },
    tabs() {
      return [
        {
          id: "0",
          name: this.isSuggested ? `Use: ${this.suggestionAgent}` : "Write",
          icon: this.isSuggested && "suggestion",
          component: "TextAreaContents",
        },
        ...(!this.isSuggested
          ? [
              {
                id: "1",
                name: `Suggestion: ${this.suggestionAgent}`,
                icon: "suggestion",
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
