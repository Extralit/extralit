import { readFileSync } from "node:fs";
import { dirname, resolve as resolvePath } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import { createI18n } from "vue-i18n";
import ReviewProvenance from "./ReviewProvenance.vue";
// Real message catalog (not the `#key#`-echoing global test stub from test/setup.ts,
// which would make this regression test hollow: it never actually looks a key up, so it
// can never fail when a key is deleted from en.js). A real vue-i18n instance built from
// the real catalog falls back to rendering the raw key when a message is missing, which is
// exactly the silent regression this test needs to catch: ReviewProvenance.vue looks its
// key up dynamically — `$t(`review.${source}`)` — so a plain grep over en.js for the
// literal strings "review.response"/"review.suggestion" finds nothing, and the previous
// i18n cleanup deleted both keys as "unreferenced".
import en from "~/translation/en";

// Under this repo's Vitest/Vite pipeline (@nuxtjs/i18n's build-time transform), the
// imported `en` module is precompiled: leaf message strings become message-compiler AST
// nodes, not plain strings. That's fine for feeding into `createI18n` (vue-i18n resolves
// them the same way the running app does) but means `en.review.response` itself isn't a
// bare string to assert against here — hence the expected labels below are asserted
// literally, and separately cross-checked against the raw source text of en.js.
//
// The compiler also mutates its input messages object in place (caching compiled nodes
// over the original values); `en` is the real, singleton-cached module export, so mutating
// it here would corrupt every other spec that imports translation/en. Deep-clone first.
// `@nuxtjs/i18n`'s generated module augmentation types `messages` against every
// configured locale (en/de/es/ja) — this spec only needs `en`, so the rest are empty.
const i18n = createI18n({
  legacy: false,
  locale: "en",
  fallbackLocale: "en",
  messages: { en: structuredClone(en), de: {}, es: {}, ja: {} },
});

const mountProvenance = (source: "response" | "suggestion") =>
  mount(ReviewProvenance, {
    props: { source, provenance: null },
    // Override the repo-wide `$t` -> `#key#` stub (test/setup.ts) with the real vue-i18n
    // `t` resolved against the actual en.js catalog, for this mount only.
    global: { mocks: { $t: i18n.global.t } },
  });

// Original values recovered verbatim from git (293466ae8^:extralit-frontend/translation/en.js).
const EXPECTED = { response: "Response", suggestion: "Suggestion" } as const;

// Resolved relative to this spec file (not `process.cwd()`), so the check doesn't ENOENT when
// vitest is invoked from a different directory (e.g. the monorepo root) than
// `extralit-frontend/`. Deliberately avoids `new URL(relative, import.meta.url)`: this spec's
// `happy-dom` test environment overrides the global `URL` constructor (and `node:url`'s
// browser-shimmed `URL` re-export follows it) to resolve relative references against the
// fake `http://localhost:3000` test document location instead of the given `file:` base.
const en_js_path = resolvePath(dirname(fileURLToPath(import.meta.url)), "../../../translation/en.js");
const en_js_source = readFileSync(en_js_path, "utf-8");
// Scoped to the `review: { ... }` block specifically — matching against the whole file would
// also be satisfied by an identically-valued pair under any OTHER namespace (en.js already
// has a near-miss: `response: "Response value"` elsewhere), so it would never actually pin
// `review.suggestion`/`review.response`.
const reviewBlockMatch = en_js_source.match(/\breview:\s*{([^}]*)}/);
if (!reviewBlockMatch) {
  throw new Error(`Could not locate a top-level "review: { ... }" block in ${en_js_path}`);
}
const reviewBlockSource = reviewBlockMatch[1];

describe("ReviewProvenance dynamic source lookup ($t(`review.${source}`))", () => {
  it.each(["response", "suggestion"] as const)(
    "resolves the %s provenance label from the real catalog, not the raw key",
    (source) => {
      const wrapper = mountProvenance(source);

      expect(wrapper.text()).toContain(EXPECTED[source]);
      expect(wrapper.text()).not.toContain(`review.${source}`);
    }
  );

  it("keeps both review.suggestion and review.response present in the imported catalog's structure", () => {
    // Asserts against the imported object's actual structure (post `@nuxtjs/i18n` build-time
    // transform) rather than only regexing source text, so a key removed from `en.review` —
    // or moved to a differently-shaped export — fails here directly.
    expect(Object.keys(en.review)).toEqual(expect.arrayContaining(["suggestion", "response"]));
  });

  it.each(["response", "suggestion"] as const)(
    "keeps review.%s present with its expected value in the checked-in en.js catalog's review block",
    (key) => {
      // Belt-and-suspenders: assert directly against the source text, independent of the
      // build-time i18n transform above (and scoped to the `review` block only, so it can't
      // be satisfied by a same-valued key under a different namespace), so a future edit to
      // en.js is caught even if the transform/mount plumbing above ever changes.
      expect(reviewBlockSource).toMatch(new RegExp(`\\b${key}:\\s*"${EXPECTED[key]}"`));
    }
  );
});
