import { mount } from "@vue/test-utils";
import BaseBadge from "./BaseBadge.vue";

const ButtonStub = { template: '<button class="--clickable"><slot /></button>' };

describe("BaseBadge", () => {
  it("is not clickable when no listener is attached", async () => {
    const wrapper = mount(BaseBadge, {
      props: { text: "hello" },
      global: { stubs: { BaseButton: ButtonStub } },
    });
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.clickable).toBe(false);
    expect(wrapper.find("p").exists()).toBe(true);
    expect(wrapper.find(".--clickable").exists()).toBe(false);
  });

  it("is clickable when onOnClick attr is present (Vue 3 @on-click normalization)", async () => {
    // In Vue 3, a parent binding `@on-click="handler"` is compiled into the attrs object
    // as `onOnClick` (on + PascalCase). Passing it via `attrs` in the test mirrors exactly
    // what the compiled parent template produces.
    const wrapper = mount(BaseBadge, {
      props: { text: "hello" },
      attrs: { onOnClick: () => {} },
      global: { stubs: { BaseButton: ButtonStub } },
    });
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.clickable).toBe(true);
    expect(wrapper.find(".--clickable").exists()).toBe(true);
  });
});
