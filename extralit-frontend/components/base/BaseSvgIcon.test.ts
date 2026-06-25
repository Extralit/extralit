import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import BaseSvgIcon from "./BaseSvgIcon.vue";

describe("BaseSvgIcon", () => {
  it("renders an svg for a known icon name with the name as data attribute", () => {
    const wrapper = mount(BaseSvgIcon, { props: { name: "check", width: 16, height: 16 } });
    expect(wrapper.find("svg").exists()).toBe(true);
    expect(wrapper.attributes("data-icon")).toBe("check");
  });

  it("applies the requested width/height to the svg", () => {
    const wrapper = mount(BaseSvgIcon, { props: { name: "check", width: 16, height: 16 } });
    const svg = wrapper.find("svg");
    expect(svg.attributes("width")).toBe("16px");
    expect(svg.attributes("height")).toBe("16px");
  });

  it("recolors monochrome fills when a color is supplied", () => {
    const wrapper = mount(BaseSvgIcon, { props: { name: "check", color: "#ff0000" } });
    expect(wrapper.html()).toContain('fill="#ff0000"');
  });

  it("renders nothing for an unknown icon name", () => {
    const wrapper = mount(BaseSvgIcon, { props: { name: "definitely-not-an-icon" } });
    expect(wrapper.find("svg").exists()).toBe(false);
  });
});
