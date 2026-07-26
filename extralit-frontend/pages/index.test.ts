import { describe, expect, it, vi } from "vitest";
import HomePage from "./index.vue";

/**
 * Covers the pure part of the home tab bar: which tab ids navigate and which swap the panel
 * below the bar. That mapping was previously pinned only by `e2e/v2/extractions-nav.spec.ts`,
 * which needs a live server and a dev frontend and runs under a separate Playwright project
 * (`npm run e2e:v2`) rather than `npm test` — so a tab that routed nowhere surfaced only when
 * someone ran the full stack.
 *
 * `onTabChange` and `data()` are plain options, so they are exercised against a hand-built
 * `this` rather than a mount — the page's `setup()` pulls the whole home view-model through DI,
 * none of which this behaviour touches. `data()` is the real one, so a tab added without its
 * route (or a route pointing at no tab) fails here.
 */
const makeContext = () => {
  const push = vi.fn();
  const context: Record<string, unknown> = {
    $t: (key: string) => key,
    $router: { push },
  };
  Object.assign(context, (HomePage as unknown as { data: () => object }).data.call(context));
  return { context, push };
};

const changeTab = (context: Record<string, unknown>, tabId: string) =>
  (HomePage as unknown as { methods: { onTabChange: (id: string) => void } }).methods.onTabChange.call(context, tabId);

describe("home tab navigation", () => {
  it("pushes the route for a navigation tab and leaves the active panel alone", () => {
    const { context, push } = makeContext();
    const before = context.activeTab;

    changeTab(context, "extractions");

    expect(push).toHaveBeenCalledWith("/extractions");
    expect(context.activeTab).toBe(before);
  });

  it("sets the active tab for a content tab without navigating", () => {
    const { context, push } = makeContext();

    changeTab(context, "documents");

    expect(push).not.toHaveBeenCalled();
    expect((context.activeTab as { id: string }).id).toBe("documents");
  });

  it("ignores an unknown tab id rather than blanking the panel", () => {
    // The old id->route map allowed a tab id that matched neither a route nor a panel to fall
    // through and set `activeTab` to something with no `home__tab-content` branch — a blank
    // page instead of a visible error.
    const { context, push } = makeContext();
    const before = context.activeTab;

    changeTab(context, "does-not-exist");

    expect(push).not.toHaveBeenCalled();
    expect(context.activeTab).toBe(before);
  });

  it("gives every tab either a route or a panel branch, so none can render blank", () => {
    const { context } = makeContext();
    const tabs = context.tabs as Array<{ id: string; route?: string }>;
    const PANEL_TAB_IDS = ["datasets", "documents"]; // the `home__tab-content` branches

    expect(tabs.map((tab) => tab.id)).toEqual(["datasets", "documents", "schemas", "extractions"]);
    for (const tab of tabs) {
      expect(Boolean(tab.route) || PANEL_TAB_IDS.includes(tab.id)).toBe(true);
    }
  });
});
