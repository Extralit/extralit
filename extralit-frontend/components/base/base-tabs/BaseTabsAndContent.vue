<template>
  <div>
    <BaseTabs :tabs="tabs" :active-tab="currentTab" :tab-size="tabSize" @change-tab="getSelectedTab" />
    <transition name="fade" mode="out-in" appear>
      <slot :current-component="currentComponent" />
    </transition>
  </div>
</template>
<script>
export default {
  props: {
    tabs: {
      type: Array,
      required: true,
    },
    tabSize: {
      type: String,
    },
  },
  data() {
    return {
      currentTab: this.tabs[0],
    };
  },
  computed: {
    currentComponent() {
      return this.currentTab.component;
    },
  },
  watch: {
    currentTab() {
      this.$emit("onChanged", this.currentTab.id);
    },
  },
  methods: {
    getSelectedTab(id) {
      this.currentTab = this.tabs.find((tab) => tab.id === id);
    },
  },
  mounted() {
    this.$emit("onLoaded");

    this.$emit("onChanged", this.currentTab.id);
  },
};
</script>
