import Vue from "vue";
import Toast from "./Toast.vue";
import eventBus from "./bus";

export const toast = (globalOptions = {}) => {
  return {
    open(options) {
      const props = {
        ...globalOptions,
        ...options,
      };

      return new (Vue.extend(Toast))({
        el: document.createElement("div"),
        propsData: props,
      });
    },
    clear() {
      eventBus.$emit("toast.clear");
    },
  };
};
