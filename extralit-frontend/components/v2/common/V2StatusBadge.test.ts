import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import V2StatusBadge from "./V2StatusBadge.vue";

const mountBadge = (status: string) =>
  mount(V2StatusBadge, {
    props: { status },
    global: {
      stubs: { BaseBadge: { name: "BaseBadge", template: "<span><slot/>{{ text }}</span>", props: ["text", "color"] } },
    },
  });

describe("V2StatusBadge", () => {
  it("passes the status through as the badge text", () => {
    expect(mountBadge("published").text()).toContain("published");
  });

  it("maps known statuses to distinct token colors", () => {
    const color = (s: string) => mountBadge(s).findComponent({ name: "BaseBadge" }).props("color");
    expect(color("completed")).not.toBe(color("discarded"));
  });
});
