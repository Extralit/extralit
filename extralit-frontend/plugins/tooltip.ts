import { createApp, h } from "vue";
import { defineNuxtPlugin } from "#app";
import BaseFixedTooltip from "@/components/base/base-tooltip/BaseFixedTooltip.vue";

type TooltipApp = { app: ReturnType<typeof createApp>; mountPoint: HTMLElement };

export default defineNuxtPlugin((nuxtApp) => {
  const instances = new WeakMap<HTMLElement, TooltipApp>();

  const create = (element: HTMLElement, binding: { value: { content: unknown; open: unknown } }) => {
    const app = createApp({
      render: () =>
        h(BaseFixedTooltip, {
          content: binding.value.content,
          open: binding.value.open,
          triggerElement: element,
        }),
    });

    const mountPoint = document.createElement("div");
    document.body.appendChild(mountPoint);
    app.mount(mountPoint);

    instances.set(element, { app, mountPoint });
  };

  const destroy = (element: HTMLElement) => {
    const instance = instances.get(element);
    if (!instance) return;
    instance.app.unmount();
    instance.mountPoint.remove();
    instances.delete(element);
  };

  nuxtApp.vueApp.directive("tooltip", {
    mounted(element: HTMLElement, binding) {
      create(element, binding as never);
    },
    updated(element: HTMLElement, binding) {
      destroy(element);
      create(element, binding as never);
    },
    unmounted(element: HTMLElement) {
      destroy(element);
    },
  });
});
