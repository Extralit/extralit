<template>
  <div class="fields">
    <div v-for="group in fieldsWithTabs" :key="group[0].id">
      <SpanAnnotationTextFieldComponent
        v-if="group.length == 1 && hasSpanQuestion(group[0].name)"
        :id="`${group[0].id}-${record.id}-span-field`"
        :name="group[0].name"
        :title="group[0].title"
        :fieldText="group[0].content"
        :spanQuestion="getSpanQuestion(group[0].name)"
      />
      <TextFieldComponent
        v-else-if="group.length == 1"
        :title="group[0].title"
        :fieldText="group[0].content"
        :useMarkdown="group[0].settings.use_markdown"
        :useTable="group[0].settings.use_table"
        :stringToHighlight="searchValue"
      />
      
      <BaseCardWithTabs 
        v-else-if="group.length > 1" 
        :tabs="group.map(field => ({ id: field.name, name: field.title, class: '--field', component: 'TextFieldComponent' }))"
      >
        <template v-slot="{ currentComponent, currentTabId }">
          <component
            :is="currentComponent"
            :key="currentTabId"
            :title="group.find(field => field.name === currentTabId)?.title"
            :fieldText="group.find(field => field.name === currentTabId)?.content"
            :useMarkdown="group.find(field => field.name === currentTabId)?.settings.use_markdown"
            :useTable="group.find(field => field.name === currentTabId)?.settings.use_table"
            :stringToHighlight="searchValue"
          />
        </template>
      </BaseCardWithTabs>
      
    </div>
  </div>
</template>
<script>
export default {
  props: {
    record: {
      type: Object,
    },
    fields: {
      type: Array,
      required: true,
    },
  },
  methods: {
    getSpanQuestion(fieldName) {
      return this.spanQuestions?.find((q) => q.settings.field === fieldName);
    },
    hasSpanQuestion(fieldName) {
      return !!this.getSpanQuestion(fieldName);
    },
  },
  computed: {
    spanQuestions() {
      return this.record?.questions.filter((q) => q.isSpanType);
    },
    searchValue() {
      return this.$route.query?._search ?? "";
    },
    fieldsWithTabs() {
      const fieldGroups = this.fields.reduce((groups, field) => {
        const prefix = field.name.split('-')[0];
        if (!groups[prefix]) {
          groups[prefix] = [];
        }
        groups[prefix].push(field);
        return groups;
      }, {});

      return Object.values(fieldGroups);
    },
  },
};
</script>
<style lang="scss" scoped>
.fields {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: $base-space;
  min-width: 0;
  height: 100%;
  min-height: 0;
}

.card-with-tabs {
  :deep(.card-with-tabs__tab.--field) {
    .button {
      font-weight: bold;
      color: palette(grey, 300);
    }
  }
}
</style>
