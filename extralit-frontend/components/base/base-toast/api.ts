import { createApp } from "vue";
import Toast from "./Toast.vue";
import eventBus from "./bus";

export const toast = (globalOptions = {}) => {
  return {
    open(options) {
      const props = {
        ...globalOptions,
        ...options,
      };

      // Vue 3 replacement for `new (Vue.extend(Toast))({ el, propsData })`.
      // The Toast component relocates its own root element into the notices
      // container on mount; `destroy` tears the app down again on close.
      const mountPoint = document.createElement("div");
      const app = createApp(Toast, {
        ...props,
        destroy: () => {
          app.unmount();
          mountPoint.remove();
        },
      });

      return app.mount(mountPoint);
    },
    clear() {
      eventBus.emit("toast.clear");
    },
  };
};
