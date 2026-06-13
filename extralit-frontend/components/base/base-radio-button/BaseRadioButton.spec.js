import { shallowMount } from "@vue/test-utils";
import BaseRadioButton from "./BaseRadioButton";

let wrapper = null;
const options = {
  props: {
    id: "id",
    name: "name",
    value: "1",
    model: "1",
  },
};
beforeEach(() => {
  wrapper = shallowMount(BaseRadioButton, options);
});

afterEach(() => {
  wrapper.unmount();
});

describe("BaseRadioButtonComponent", () => {
  it("render the component", () => {
    expect(wrapper.is(BaseRadioButton)).toBe(true);
  });
  it("bind disabled class", async () => {
    wrapper = shallowMount(BaseRadioButton, {
      props: {
        disabled: true,
      },
    });
    expect(wrapper.classes()).toContain("--disabled");
  });
  it("component is selected when model and value matched", async () => {
    expect(wrapper.vm.isSelected).toBe(true);
    expect(wrapper.props().model).toBe("1");
  });
  it("input is checked when model and value matched", async () => {
    const radioInput = wrapper.find('input[type="radio"]');
    expect(radioInput.element.checked).toBeTruthy();
  });
});
