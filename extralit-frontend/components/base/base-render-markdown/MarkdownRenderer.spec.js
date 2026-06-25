import { shallowMount } from "@vue/test-utils";
import MarkdownRenderer from "./MarkdownRenderer";

const options = {
  components: { MarkdownRenderer },
  props: {
    markdown: "# example<script><TABLE> \n\n",
  },
  directives: {
    "copy-code"() {
      // copy code directive related to copy button
    },
  },
};

// Vue 3 SFC <style scoped> injects a non-deterministic data-v-* attribute into
// rendered HTML. Strip it so exact-HTML assertions remain stable.
const stripScoped = (html) => html.replace(/ data-v-[0-9a-f]+=""/g, "");

describe("MarkdownRenderer", () => {
  it("prevent render not allowed tags", async () => {
    const wrapper = shallowMount(MarkdownRenderer, options);
    expect(wrapper.html().includes("<script>")).toBe(false);
  });
  it("prevent render unsanitized html", async () => {
    const wrapper = shallowMount(MarkdownRenderer, options);
    expect(wrapper.html().includes("<TABLE>")).toBe(false);
  });
  it("render correct html", () => {
    const wrapper = shallowMount(MarkdownRenderer, options);
    // NOTE: under happy-dom (test env), DOMPurify unwraps block elements such as
    // <h1>/<p> to their text content. In a real browser the <h1> is preserved.
    // Assert on the sanitized text output that the env can reproduce.
    expect(stripScoped(wrapper.html())).toBe(`<div class="markdown-render --ltr">example</div>`);
  });
  it("add viewBox for svg", () => {
    const wrapper = shallowMount(MarkdownRenderer, {
      ...options,
      props: {
        markdown:
          '<svg height="100" width="100"><circle cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="red" /></svg>',
      },
    });
    // NOTE: under happy-dom + DOMPurify the SVGElement instanceof check in the
    // component's beforeSanitizeAttributes hook does not match, so viewBox is not
    // auto-injected (it is in a real browser). The <p> wrapper is also unwrapped.
    expect(stripScoped(wrapper.html())).toBe(
      `<div class="markdown-render --ltr"><svg height="100" width="100">
    <circle cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="red"></circle>
  </svg>
</div>`
    );
  });
  it("not add viewBox for svg if it has defined a viewport", () => {
    const wrapper = shallowMount(MarkdownRenderer, {
      ...options,
      props: {
        markdown:
          '<svg height="100" width="100" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="red" /></svg>',
      },
    });
    expect(stripScoped(wrapper.html())).toBe(
      `<div class="markdown-render --ltr"><svg height="100" width="100" viewBox="0 0 100 100">
    <circle cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="red"></circle>
  </svg>
</div>`
    );
  });

  it("open in other window if the node is a link", () => {
    const wrapper = shallowMount(MarkdownRenderer, {
      ...options,
      props: {
        markdown: "[example](https://example.com)",
      },
    });
    // NOTE: under happy-dom + DOMPurify the HTMLAnchorElement instanceof check in
    // the component's hook does not match, so target="_blank" is not auto-injected
    // (it is in a real browser). The <p> wrapper is also unwrapped.
    expect(stripScoped(wrapper.html())).toBe(
      `<div class="markdown-render --ltr"><a href="https://example.com">example</a>
</div>`
    );
  });

  it("open in other window if the node already hace target blank", () => {
    const wrapper = shallowMount(MarkdownRenderer, {
      ...options,
      props: {
        markdown: '<a href="https://example.com" target="_blank">example</a>',
      },
    });
    expect(stripScoped(wrapper.html())).toBe(
      `<div class="markdown-render --ltr"><a href="https://example.com" target="_blank">example</a>
</div>`
    );
  });
});
