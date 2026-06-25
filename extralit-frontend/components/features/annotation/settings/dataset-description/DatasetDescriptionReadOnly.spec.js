import { shallowMount } from "@vue/test-utils";
import DatasetDescriptionReadOnly from "./DatasetDescriptionReadOnly";

let wrapper = null;
const options = {
  global: {
    stubs: ["MarkdownRenderer"],
    mocks: {
      $t: (msg) => msg,
    },
  },
  props: {
    guidelines: "Lorem ipsum",
  },
};
beforeEach(() => {
  wrapper = shallowMount(DatasetDescriptionReadOnly, options);
});

afterEach(() => {
  wrapper.unmount();
});

describe("DatasetDescriptionReadonlyComponent", () => {
  it("render the component", () => {
    expect(wrapper.findComponent(DatasetDescriptionReadOnly).exists()).toBe(true);
  });
});
