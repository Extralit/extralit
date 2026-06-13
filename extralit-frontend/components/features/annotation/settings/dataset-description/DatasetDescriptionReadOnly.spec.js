import { shallowMount } from "@vue/test-utils";
import DatasetDescriptionReadOnly from "./DatasetDescriptionReadOnly";

let wrapper = null;
const options = {
  stubs: ["MarkdownRenderer"],
  props: {
    guidelines: "Lorem ipsum",
  },
  mocks: {
    $t: (msg) => msg,
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
    expect(wrapper.is(DatasetDescriptionReadOnly)).toBe(true);
  });
});
