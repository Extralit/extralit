import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import en from "~/translation/en";
import StatusBadge, { STATUS_TOKENS } from "./StatusBadge.vue";

const mountBadge = (status: string) =>
  mount(StatusBadge, {
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

describe("StatusBadge colors", () => {
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
});

const themesPath = resolve(dirname(fileURLToPath(import.meta.url)), "../../../assets/css/themes.css");

const parseBlocks = (css: string): { selector: string; tokens: Record<string, string> }[] =>
  [...css.matchAll(/(?:^|\n)\s*([^{}\n][^{}]*?)\s*\{([^{}]*)\}/g)].map(([, selector, body]) => ({
    selector: selector.trim(),
    tokens: Object.fromEntries([...body.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)].map(([, k, v]) => [k, v.trim()])),
  }));

const STATUS_BLOCKS = parseBlocks(readFileSync(themesPath, "utf8")).filter(({ tokens }) =>
  Object.keys(tokens).some((token) => token.startsWith("--fg-status-"))
);

describe("StatusBadge token definitions", () => {
  it("finds every themes.css block that defines status tokens", () => {
    expect(STATUS_BLOCKS.map((b) => b.selector)).toEqual([
      ":root",
      '[data-theme="dark"]',
      '[data-theme="high-contrast"]',
    ]);
  });

  it.each([...new Set(Object.values(STATUS_TOKENS))])("defines %s in every one of those blocks", (token) => {
    for (const { selector, tokens } of STATUS_BLOCKS) {
      expect(tokens[token], `${token} is not defined in ${selector}`).toBeTruthy();
    }
  });

  it.each(STATUS_BLOCKS.map((block) => [block.selector, block] as const))(
    "resolves each status to a distinct color value within its own table under %s",
    (_selector, block) => {
      const valueOf = (status: string) => block.tokens[STATUS_TOKENS[status]];

      expect(new Set(["draft", "published"].map(valueOf)).size).toBe(2);
      expect(new Set(["pending", "completed", "discarded"].map(valueOf)).size).toBe(3);
    }
  );
});

describe("StatusBadge label", () => {
  it("has an en.js key for every status it can render", () => {
    expect(Object.keys(en.v2Status).sort()).toEqual(Object.keys(STATUS_TOKENS).sort());
  });

  it.each(Object.keys(STATUS_TOKENS))("translates %s rather than rendering the raw server value", (status) => {
    expect(propOf(status, "text")).toBe(`t:v2Status.${status}`);
  });

  it("renders an unknown status raw rather than as a missing-key string", () => {
    expect(propOf("something-new", "text")).toBe("something-new");
  });
});
