// Flat config (ESLint 10). Replaces the legacy .eslintrc.js + .eslintignore.
//
// Posture is preserved verbatim from the old config: eslint-plugin-vue's
// `flat/recommended` is all-`warn`, formatting (prettier/prettier) is `warn`, and
// `npm run lint` runs with `--quiet` so only error-level rules gate. The @nuxt/eslint
// module (project-aware auto-import globals) remains the tracked follow-up; until then
// the Nuxt 4 auto-imports are hand-declared below, as they were in .eslintrc.js.
import js from "@eslint/js";
import globals from "globals";
import pluginVue from "eslint-plugin-vue";
import vueI18n from "@intlify/eslint-plugin-vue-i18n";
import prettierRecommended from "eslint-plugin-prettier/recommended";
import vueParser from "vue-eslint-parser";
import tsParser from "@typescript-eslint/parser";
import tsPlugin from "@typescript-eslint/eslint-plugin";

const isProd = process.env.NODE_ENV === "production";

export default [
  // Global ignores (ported from .eslintignore).
  {
    ignores: [
      "node_modules/**",
      "dist/**",
      ".nuxt/**",
      ".output/**",
      "e2e/**",
      "v1/domain/entities/document/Document.ts",
      "v1/domain/usecases/get-extraction-completion-use-case.ts",
      "components/base/base-render-table/**",
      "v2/infrastructure/api/generated/**",
    ],
  },

  js.configs.recommended,
  ...pluginVue.configs["flat/recommended"],
  ...vueI18n.configs["flat/recommended"],

  // Shared language options, globals, settings and base rules for every file.
  {
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: {
        ...globals.node,
        ...globals.browser,
        ...globals.jest,
        $nuxt: "readonly",
        vi: "readonly",
        // Nuxt 4 auto-imports, hand-declared to satisfy no-undef. This list can drift;
        // the real fix is adopting `@nuxt/eslint` (flat config), which auto-generates
        // these globals from the build manifest. Tracked as follow-up, not done here.
        defineNuxtPlugin: "readonly",
        defineNuxtRouteMiddleware: "readonly",
        definePageMeta: "readonly",
        navigateTo: "readonly",
        abortNavigation: "readonly",
        useNuxtApp: "readonly",
        useRuntimeConfig: "readonly",
        useRoute: "readonly",
        useRouter: "readonly",
        useState: "readonly",
        useCookie: "readonly",
        useHead: "readonly",
        useSeoMeta: "readonly",
        useError: "readonly",
        createError: "readonly",
        clearError: "readonly",
        showError: "readonly",
      },
    },
    settings: {
      "vue-i18n": {
        localeDir: "./translation/*.js",
      },
    },
    rules: {
      "no-console": isProd ? "error" : "off",
      "no-debugger": isProd ? "error" : "off",
      "prefer-const": "warn",
      "prefer-arrow-callback": "warn",
      "no-unused-vars": ["warn", { ignoreRestSiblings: true }],
      "@intlify/vue-i18n/no-raw-text": "off",
      "@intlify/vue-i18n/no-v-html": "off",
      "@intlify/vue-i18n/no-missing-keys": "warn",
      "vue/attributes-order": [
        "warn",
        {
          order: [
            "DEFINITION",
            "LIST_RENDERING",
            "CONDITIONALS",
            "RENDER_MODIFIERS",
            "GLOBAL",
            "UNIQUE",
            "TWO_WAY_BINDING",
            "OTHER_DIRECTIVES",
            "OTHER_ATTR",
            "EVENTS",
            "CONTENT",
          ],
          alphabetical: false,
        },
      ],
    },
  },

  // `.vue` files: vue-eslint-parser with the TS parser for <script lang="ts">.
  {
    files: ["**/*.vue"],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tsParser,
        ecmaVersion: 2022,
        sourceType: "module",
      },
    },
  },

  // TypeScript files: @typescript-eslint recommended (scoped to *.ts, as before).
  ...tsPlugin.configs["flat/recommended"].map((c) => ({ ...c, files: ["**/*.ts"] })),
  {
    files: ["**/*.ts"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        // No `project` here: every enabled @typescript-eslint rule is syntactic
        // (the non-type-checked `recommended` set), so type-aware parsing would only
        // make lint multi-minutes slower for zero new findings. Type errors are caught
        // separately by `nuxi typecheck` (vue-tsc).
        ecmaVersion: 2022,
        sourceType: "module",
      },
    },
    rules: {
      quotes: ["warn", "double"],
      semi: ["warn", "always"],
      "no-useless-constructor": "off",
      "space-before-function-paren": "off",
      "no-throw-literal": "off",
      "no-new": "off",
      // Ambient `declare namespace CSS { ... }` global augmentations (CSS Custom
      // Highlight API) can't be expressed as ES modules; allow declaration-only namespaces.
      "@typescript-eslint/no-namespace": ["error", { allowDeclarations: true }],
      // typescript-eslint v8 promotes these from `warn` (their v5 severity, which the
      // old `lint --quiet` hid) to `error`. The codebase predates strict typing; keep
      // them advisory so this bump stays behaviour-only. Tracked follow-up: type the
      // ~205 `any`s. `_`-prefixed names are treated as intentionally unused.
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { ignoreRestSiblings: true, argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
    },
  },

  // Prettier last: turns off formatting-conflicting rules and adds prettier/prettier.
  // Kept advisory (`warn`) — `npm run format` is the source of truth, and `lint --quiet`
  // stays focused on correctness.
  prettierRecommended,
  {
    rules: {
      "prettier/prettier": "warn",
    },
  },

  // ── Rules newly promoted to `error` by this toolchain bump (eslint 8->10,
  //    eslint-plugin-vue 8->10) that the previous setup either did not enable or that
  //    eslint-plugin-nuxt's preset disabled. They flag PRE-EXISTING patterns (legacy
  //    prop mutation, single-word Nuxt page names, a stray Vue 2 lifecycle hook, etc.),
  //    not regressions introduced here. Kept advisory so the bump is behaviour-only and
  //    `lint --quiet` stays green; each is a tracked follow-up. They remain visible in
  //    editors and in a non-`--quiet` `eslint .` run. Several are genuine bugs worth
  //    fixing separately: vue/require-v-for-key, vue/valid-template-root,
  //    vue/no-side-effects-in-computed-properties, vue/no-deprecated-destroyed-lifecycle.
  {
    rules: {
      // eslint 9/10 core additions to `recommended`
      "no-useless-assignment": "warn",
      "no-constant-binary-expression": "warn",
      "preserve-caught-error": "warn",
      // Nuxt convention: pages/layouts are single-word (eslint-plugin-nuxt disabled this)
      "vue/multi-word-component-names": "off",
      // eslint-plugin-vue 10 essential/strongly-recommended, firing on legacy patterns
      "vue/no-mutating-props": "warn",
      "vue/return-in-computed-property": "warn",
      "vue/no-v-text-v-html-on-component": "warn",
      "vue/valid-template-root": "warn",
      "vue/valid-next-tick": "warn",
      "vue/require-valid-default-prop": "warn",
      "vue/require-v-for-key": "warn",
      "vue/require-prop-type-constructor": "warn",
      "vue/no-unused-components": "warn",
      "vue/no-side-effects-in-computed-properties": "warn",
      "vue/no-parsing-error": "warn",
      "vue/no-deprecated-destroyed-lifecycle": "warn",
    },
  },
];
