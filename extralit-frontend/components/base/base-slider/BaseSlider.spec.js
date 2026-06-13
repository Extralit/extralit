import { mount } from "@vue/test-utils";
import BaseSlider from "@/components/base/base-slider/BaseSlider";

function mountBaseSlider() {
  return mount(BaseSlider, {
    props: {
      slidesName: "sentences",
      slidesOrigin: ["first sentence", "second sentence"],
      itemNumber: 0,
    },
  });
}

describe("BaseSlider", () => {
  const spy = vi.spyOn(console, "error");
  afterEach(() => spy.mockReset());

  test("renders properly", () => {
    const wrapper = mountBaseSlider();
    expect(wrapper.html()).toMatchSnapshot();
  });
});
