<template>
  <div class="record">
    <div class="record__content">
      <slot></slot>
      <div
        v-for="group in fieldsWithTabs"
      >
        <TextFieldComponent
          v-if="group.length == 1"
          :title="group[0].title"
          :fieldText="group[0].content"
          :useMarkdown="group[0].settings.use_markdown"
          :useTable="group[0].settings.use_table"
          :stringToHighlight="searchValue"
        />
        
        <BaseCardWithTabs 
          v-else-if="group.length > 1" 
          :tabs="group.map(field => ({ id: field.name, name: field.title, component: 'TextFieldComponent' }))"
        >
          <template v-slot="{ currentComponent, currentTabId }">
            <component
              :is="currentComponent"
              :key="currentTabId"
              :title="group.find(field => field.name === currentTabId).title"
              :fieldText="group.find(field => field.name === currentTabId).content"
              :useMarkdown="group.find(field => field.name === currentTabId).settings.use_markdown"
              :useTable="group.find(field => field.name === currentTabId).settings.use_table"
              :stringToHighlight="searchValue"
            />
          </template>
        </BaseCardWithTabs>
        
      </div>
    </div>
  </div>
</template>
<script>
export default {
  props: {
    fields: {
      type: Array,
      required: true,
    },
  },
  computed: {
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
.record {
  background: palette(white);
  border: 1px solid palette(grey, 600);
  border-radius: $border-radius-m;
  min-height: 0;
  &__content {
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow: auto;
    gap: $base-space * 2;
    padding: $base-space * 2;
    border-radius: $border-radius-m;
  }
}
</style>
