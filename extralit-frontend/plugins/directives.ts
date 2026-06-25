import { h, render } from "vue";
import { defineNuxtPlugin } from "#app";
import BaseCode from "~/components/base/base-code/BaseCode.vue";
import { useClipboard } from "~/v1/infrastructure/services/useClipboard";

// Former plugins/directives/*.directive.{ts,js}, ported to Nuxt 4 (bind -> mounted,
// update -> updated). tooltip and click-outside are their own plugin files.
export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.vueApp.directive("badge", {
    mounted(
      element: HTMLElement,
      binding: {
        value: {
          showBadge: boolean;
          verticalPosition: string;
          horizontalPosition: string;
          backgroundColor: string;
          borderColor: string;
          size: string;
        };
      }
    ) {
      const { showBadge } = binding.value;
      if (!showBadge) return;

      const { verticalPosition, horizontalPosition, backgroundColor, borderColor, size } = binding.value;

      element.style.position = "relative";
      const badge = document.createElement("div");
      badge.setAttribute("id", `${element.id}Badge`);
      badge.style.position = "absolute";
      badge.style.backgroundColor = backgroundColor || "#ff675f";
      badge.style.width = size || "14px";
      badge.style.height = size || "14px";
      badge.style.borderRadius = "5em";
      badge.style.border = `2px ${borderColor ?? "transparent"} solid`;

      switch (verticalPosition) {
        case "top":
          badge.style.top = "-3px";
          break;
        case "bottom":
          badge.style.bottom = "-3px";
          break;
      }

      switch (horizontalPosition) {
        case "right":
          badge.style.right = "-3px";
          break;
        case "left":
          badge.style.left = "-3px";
          break;
      }

      element.appendChild(badge);
    },
  });

  nuxtApp.vueApp.directive("circle", {
    mounted(element: HTMLElement, binding) {
      let circleDiameter = "0px";
      let fontSize = "1rem";
      let borderColor = "var(--bg-opacity-1)";

      const { size } = binding?.value ?? { size: "SMALL" };

      switch (size) {
        case "MINI":
          circleDiameter = "26px";
          fontSize = "0.6rem";
          borderColor = "var(--color-avatar-fg)";
          break;
        case "SMALL":
          circleDiameter = "34px";
          fontSize = "1rem";
          break;
        case "MEDIUM":
          circleDiameter = "45px";
          break;
        default:
          circleDiameter = "34px";
      }

      element.style.display = "flex";
      element.style.alignItems = "center";
      element.style.justifyContent = "center";
      element.style.height = circleDiameter;
      element.style.width = circleDiameter;
      element.style.borderRadius = "50%";
      element.style.border = `1px solid ${borderColor}`;
      element.style.fontSize = fontSize;
      element.style.fontWeight = "500";
      element.style.lineHeight = circleDiameter;
      element.style.textTransform = "uppercase";
    },
  });

  nuxtApp.vueApp.directive("required-field", {
    mounted(element: HTMLElement, binding: { value: { show: boolean; color: string } }) {
      const span = document.createElement("span");
      span.textContent = " *";
      span.style.color = binding.value.color;
      span.setAttribute("title", "Required response");
      span.setAttribute("role", "mark");
      element.appendChild(span);
      span.style.display = binding.value.show ? "inline" : "none";
    },
    updated(element: HTMLElement, binding) {
      const span = element.querySelector("span");
      if (span) {
        span.style.display = binding.value.show ? "inline" : "none";
      }
    },
  });

  // copy-code: overlays a BaseCode "copy" button on each <pre>. Rendered with the
  // host app's appContext so it keeps $copyToClipboard, i18n and global components.
  nuxtApp.vueApp.directive("copy-code", {
    mounted(el: HTMLElement, binding) {
      const { copy } = useClipboard();
      const appContext = (binding as { instance?: { $?: { appContext?: unknown } } }).instance?.$?.appContext;

      for (const pre of Array.from(el.getElementsByTagName("PRE")) as HTMLElement[]) {
        const code = (pre.children[0] as HTMLElement)?.innerText ?? pre.innerText;

        const container = document.createElement("div");
        container.style.position = "relative";

        const holder = document.createElement("div");
        const vnode = h(BaseCode, { code, copyToClipboard: copy });
        if (appContext) (vnode as { appContext?: unknown }).appContext = appContext;
        render(vnode, holder);

        pre.parentNode?.replaceChild(container, pre);
        container.appendChild(pre);
        if (holder.firstElementChild) container.appendChild(holder.firstElementChild);
      }
    },
  });
});
