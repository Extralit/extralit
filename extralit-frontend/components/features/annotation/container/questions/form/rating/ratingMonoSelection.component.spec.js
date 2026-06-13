import { shallowMount } from "@vue/test-utils";
import RatingMonoSelectionComponent from "./RatingMonoSelection.component";

let wrapper = null;
const options = {
  global: {
    stubs: {
      // Render the default slot so the inner <input>/<label> are present
      // (VTU v2 stubs drop slot content by default, unlike VTU v1).
      BaseTooltip: { template: "<div><slot /></div>" },
    },
  },
  props: {
    options: [
      { id: "helpfulness_reply_1_1", value: 1, text: 1, isSelected: false },
      { id: "helpfulness_reply_1_2", value: 2, text: 2, isSelected: false },
      { id: "helpfulness_reply_1_3", value: 3, text: 3, isSelected: false },
      { id: "helpfulness_reply_1_4", value: 4, text: 4, isSelected: false },
      { id: "helpfulness_reply_1_5", value: 5, text: 5, isSelected: false },
    ],
  },
};
beforeEach(() => {
  wrapper = shallowMount(RatingMonoSelectionComponent, options);
});

afterEach(() => {
  wrapper.unmount();
});

describe("RatingMonoSelectionComponent", () => {
  it("render the component and the rating options", () => {
    expect(wrapper.findComponent(RatingMonoSelectionComponent).exists()).toBe(true);

    const labelsWrapper = wrapper.findAll("label");
    expect(labelsWrapper[0].classes()).toContain("label-text");
    expect(labelsWrapper[0].classes()).not.toContain("label-active");
    expect(labelsWrapper[0].text()).toBe("1");

    expect(labelsWrapper[1].classes()).toContain("label-text");
    expect(labelsWrapper[1].classes()).not.toContain("label-active");
    expect(labelsWrapper[1].text()).toBe("2");

    expect(labelsWrapper[2].classes()).toContain("label-text");
    expect(labelsWrapper[2].classes()).not.toContain("label-active");
    expect(labelsWrapper[2].text()).toBe("3");

    expect(labelsWrapper[3].classes()).toContain("label-text");
    expect(labelsWrapper[3].classes()).not.toContain("label-active");
    expect(labelsWrapper[3].text()).toBe("4");

    expect(labelsWrapper[4].classes()).toContain("label-text");
    expect(labelsWrapper[4].classes()).not.toContain("label-active");
    expect(labelsWrapper[4].text()).toBe("5");

    expect(labelsWrapper.length).toBe(5);
  });
  it("update the flag 'isSelected' of the corresponding checkbox option when user click (no items have been selected)", async () => {
    const checkbox1 = wrapper.find("#helpfulness_reply_1_1");
    const checkbox2 = wrapper.find("#helpfulness_reply_1_2");
    const checkbox3 = wrapper.find("#helpfulness_reply_1_3");
    const checkbox4 = wrapper.find("#helpfulness_reply_1_4");
    const checkbox5 = wrapper.find("#helpfulness_reply_1_5");

    expect(wrapper.vm.options).toStrictEqual([
      { id: "helpfulness_reply_1_1", value: 1, text: 1, isSelected: false },
      { id: "helpfulness_reply_1_2", value: 2, text: 2, isSelected: false },
      { id: "helpfulness_reply_1_3", value: 3, text: 3, isSelected: false },
      { id: "helpfulness_reply_1_4", value: 4, text: 4, isSelected: false },
      { id: "helpfulness_reply_1_5", value: 5, text: 5, isSelected: false },
    ]);

    await checkbox1.setChecked();

    expect(wrapper.vm.options).toStrictEqual([
      { id: "helpfulness_reply_1_1", value: 1, text: 1, isSelected: true },
      { id: "helpfulness_reply_1_2", value: 2, text: 2, isSelected: false },
      { id: "helpfulness_reply_1_3", value: 3, text: 3, isSelected: false },
      { id: "helpfulness_reply_1_4", value: 4, text: 4, isSelected: false },
      { id: "helpfulness_reply_1_5", value: 5, text: 5, isSelected: false },
    ]);

    expect(checkbox1.element.checked).toBeTruthy();
    expect(checkbox2.element.checked).toBeFalsy();
    expect(checkbox3.element.checked).toBeFalsy();
    expect(checkbox4.element.checked).toBeFalsy();
    expect(checkbox5.element.checked).toBeFalsy();

    const labelsWrapper = wrapper.findAll("label");
    expect(labelsWrapper[0].classes()).toContain("label-active");
    expect(labelsWrapper[1].classes()).not.toContain("label-active");
    expect(labelsWrapper[2].classes()).not.toContain("label-active");
    expect(labelsWrapper[3].classes()).not.toContain("label-active");
    expect(labelsWrapper[4].classes()).not.toContain("label-active");
    expect(labelsWrapper.length).toBe(5);
  });
  it("update the flag 'isSelected' of the corresponding checkbox which have been selected previously => unselect a select checkbox", async () => {
    const checkbox1 = wrapper.find("#helpfulness_reply_1_1");
    const checkbox2 = wrapper.find("#helpfulness_reply_1_2");
    const checkbox3 = wrapper.find("#helpfulness_reply_1_3");
    const checkbox4 = wrapper.find("#helpfulness_reply_1_4");
    const checkbox5 = wrapper.find("#helpfulness_reply_1_5");

    await checkbox1.setChecked(true);
    await checkbox1.setChecked(false);

    expect(checkbox1.element.checked).toBeFalsy();
    expect(checkbox2.element.checked).toBeFalsy();
    expect(checkbox3.element.checked).toBeFalsy();
    expect(checkbox4.element.checked).toBeFalsy();
    expect(checkbox5.element.checked).toBeFalsy();

    const labelsWrapper = wrapper.findAll("label");
    expect(labelsWrapper[0].classes()).not.toContain("label-active");
    expect(labelsWrapper[1].classes()).not.toContain("label-active");
    expect(labelsWrapper[2].classes()).not.toContain("label-active");
    expect(labelsWrapper[3].classes()).not.toContain("label-active");
    expect(labelsWrapper[4].classes()).not.toContain("label-active");
    expect(labelsWrapper.length).toBe(5);
  });
  it("update the flag 'isSelected' of the corresponding checkbox which have been selected previously => ensure that only one checkbox is checked at a time", async () => {
    const checkbox1 = wrapper.find("#helpfulness_reply_1_1");
    const checkbox2 = wrapper.find("#helpfulness_reply_1_2");
    const checkbox3 = wrapper.find("#helpfulness_reply_1_3");
    const checkbox4 = wrapper.find("#helpfulness_reply_1_4");
    const checkbox5 = wrapper.find("#helpfulness_reply_1_5");

    await checkbox1.setChecked(true);
    await checkbox5.setChecked(true);

    expect(checkbox1.element.checked).toBeFalsy();
    expect(checkbox2.element.checked).toBeFalsy();
    expect(checkbox3.element.checked).toBeFalsy();
    expect(checkbox4.element.checked).toBeFalsy();
    expect(checkbox5.element.checked).toBeTruthy();

    const labelsWrapper = wrapper.findAll("label");
    expect(labelsWrapper[0].classes()).not.toContain("label-active");
    expect(labelsWrapper[1].classes()).not.toContain("label-active");
    expect(labelsWrapper[2].classes()).not.toContain("label-active");
    expect(labelsWrapper[3].classes()).not.toContain("label-active");
    expect(labelsWrapper[4].classes()).toContain("label-active");
    expect(labelsWrapper.length).toBe(5);
  });
});
