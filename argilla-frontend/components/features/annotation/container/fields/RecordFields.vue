<template>
  <div class="fields">
    <div
      v-for="group in fieldsWithTabs"
      :class="[group[0]?.isImageType ? 'fields__container--image' : '']"
      :key="group[0].id"
    >
      <SpanAnnotationTextField
<<<<<<< HEAD
        v-if="group.length == 1 && hasSpanQuestion(group[0].name)"
        :id="`${group[0].id}-${record.id}`"
        :name="group[0].name"
        :title="group[0].title"
        :fieldText="group[0].content"
        :spanQuestion="getSpanQuestion(group[0].name)"
        :searchText="recordCriteria.committed.searchText.value.text"
      />
      <TextField
        v-else-if="group[0].isTextType"
        :id="`${id}-${record.id}`"
        :title="group[0].title"
        :fieldText="group[0].content"
        :useMarkdown="group[0].settings.use_markdown"
        :useTable="group[0].settings.use_table"
=======
        v-if="hasSpanQuestion(name)"
        :id="`${id}-${record.id}`"
        :name="name"
        :title="title"
        :fieldText="content"
        :spanQuestion="getSpanQuestion(name)"
        :searchText="recordCriteria.committed.searchText.value.text"
      />
      <TextField
        v-else-if="isTextType"
        :id="`${id}-${record.id}`"
        :title="title"
        :fieldText="content"
        :useMarkdown="settings.use_markdown"
>>>>>>> v2.6.0
        :searchText="recordCriteria.committed.searchText.value.text"
        :record="record"
      />
      <ChatField
<<<<<<< HEAD
        v-else-if="group[0].isChatType"
        :id="`${id}-${record.id}`"
        :title="group[0].title"
        :useMarkdown="group[0].settings.use_markdown"
        :content="group[0].content"
=======
        v-else-if="isChatType"
        :id="`${id}-${record.id}`"
        :title="title"
        :useMarkdown="settings.use_markdown"
        :content="content"
>>>>>>> v2.6.0
        :searchText="recordCriteria.committed.searchText.value.text"
      />
      <ImageField
        v-else-if="group[0].isImageType"
        :name="group[0].name"
        :title="group[0].title"
        :content="group[0].content"
      />
      <CustomField
        v-else-if="group[0].isCustomType"
        :name="group[0].name"
        :title="group[0].title"
        :content="group[0].content"
        :sdkRecord="group[0].sdkRecord"
        :settings="group[0].settings"
      />
      <TableField
        v-else-if="group[0].isTableType"
        :name="group[0].name"
        :title="group[0].title"
        :content="group[0].content"
      />

      <BaseCardWithTabs
        v-else-if="group.length > 1"
        :tabs="group.map(field => ({ id: field.name, name: field.title, class: '--field', component: 'TextField' }))"
      >
        <template v-slot="{ currentComponent, currentTabId }">
          <component
            :is="currentComponent"
            :key="currentTabId"
            :name="group.find(field => field.name === currentTabId)?.name"
            :title="group.find(field => field.name === currentTabId)?.title"
            :fieldText="group.find(field => field.name === currentTabId)?.content"
            :useMarkdown="group.find(field => field.name === currentTabId)?.settings.use_markdown"
            :useTable="group.find(field => field.name === currentTabId)?.settings.use_table"
            :searchText="recordCriteria.committed.searchText.value.text"
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
    recordCriteria: {
      type: Object,
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
      return this.record?.questions?.filter((q) => q.isSpanType);
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
