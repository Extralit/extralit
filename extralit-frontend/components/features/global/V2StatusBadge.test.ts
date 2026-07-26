import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import V2StatusBadge, { STATUS_TOKENS } from "./V2StatusBadge.vue";

const mountBadge = (status: string) =>
  mount(V2StatusBadge, {
    props: { status },
    global: {
      stubs: {
        BaseBadge: { name: "BaseBadge", template: "<span><slot/>{{ text }}</span>", props: ["text", "color"] },
      },
      mocks: { $t: (key: string) => `t:${key}` },
    },
  });

const propOf = (status: string, prop: "color" | "text") =>
  mountBadge(status).findComponent({ name: "BaseBadge" }).props(prop);

describe("V2StatusBadge colors", () => {
  // The predecessor of this spec compared two *declaration strings* and asserted they
  // differed. They did — but both named tokens that assets/css/themes.css never defined
  // (--fg-status-active, --fg-status-danger), so both fell through to their var() fallback
  // and every status rendered the same grey. Asserting the resolved token per status, plus
  // that the token actually exists, is what makes that failure mode visible.
  it.each([
    ["draft", "--fg-status-draft"],
    ["published", "--fg-status-submitted"],
    ["pending", "--fg-status-pending"],
    ["completed", "--fg-status-submitted"],
    ["discarded", "--fg-status-discarded"],
  ])("maps %s to var(%s)", (status, token) => {
    expect(propOf(status, "color")).toBe(`var(${token})`);
  });

  it("falls back to --fg-secondary for a status it does not know", () => {
    expect(propOf("something-new", "color")).toBe("var(--fg-secondary)");
  });

  it("gives the statuses that share a table visibly different colors", () => {
    // Schemas table renders draft|published; records table renders pending|completed|discarded.
    // Within each table every status must be distinguishable. Across tables, published and
    // completed deliberately share the "done" hue.
    const distinct = (statuses: string[]) => new Set(statuses.map((s) => propOf(s, "color"))).size;

    expect(distinct(["draft", "published"])).toBe(2);
    expect(distinct(["pending", "completed", "discarded"])).toBe(3);
  });
});

describe("V2StatusBadge token definitions", () => {
  const themes = readFileSync(resolve(__dirname, "../../../assets/css/themes.css"), "utf8");

  // themes.css carries three independent token blocks. Defining a token in only some of them
  // silently breaks the others, which is invisible in any DOM assertion.
  const blocks = [
    [":root", /^:root \{$/m],
    ["dark", /^\[data-theme="dark"\] \{$/m],
    ["high-contrast", /^\[data-theme="high-contrast"\] \{$/m],
  ] as const;

  it("finds all three theme blocks (guards this spec against a themes.css restructure)", () => {
    for (const [name, pattern] of blocks) {
      expect(themes, `theme block ${name} not found`).toMatch(pattern);
    }
  });

  it.each([...new Set(Object.values(STATUS_TOKENS))])("defines %s in every theme block", (token) => {
    // Count definitions rather than slicing blocks apart: every block that defines the token
    // contributes one `--token:`, so the count must equal the number of blocks.
    const definitions = themes.match(new RegExp(`^\\s*${token}\\s*:`, "gm")) ?? [];
    expect(definitions.length).toBe(blocks.length);
  });
});

describe("V2StatusBadge label", () => {
  it.each(Object.keys(STATUS_TOKENS))("translates %s rather than rendering the raw server value", (status) => {
    expect(propOf(status, "text")).toBe(`t:v2Status.${status}`);
  });

  it("renders an unknown status raw rather than as a missing-key string", () => {
    expect(propOf("something-new", "text")).toBe("something-new");
  });
});
