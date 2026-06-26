module.exports = {
  root: true,
  env: {
    node: true,
    browser: true,
    jest: true,
  },
  extends: [
    "eslint:recommended",
    "plugin:@intlify/vue-i18n/recommended",
    "plugin:prettier/recommended",
    "plugin:nuxt/recommended",
  ],
  plugins: ["vue"],
  settings: {
    "vue-i18n": {
      localeDir: "./translation/*.js",
    },
  },
  rules: {
    // Formatting is advisory here (parity with the *.ts override and the separate
    // `npm run format` step); keeps `lint --quiet` focused on real correctness rules.
    "prettier/prettier": "warn",
    "no-console": process.env.NODE_ENV === "production" ? "error" : "off",
    "no-debugger": process.env.NODE_ENV === "production" ? "error" : "off",
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
  globals: {
    $nuxt: true,
    vi: true,
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
  parser: "vue-eslint-parser",
  parserOptions: {
    parser: "@typescript-eslint/parser",
    ecmaVersion: 2022,
    sourceType: "module",
  },
  overrides: [
    {
      files: ["**/*.ts"],
      extends: ["plugin:@typescript-eslint/recommended", "prettier"],
      parser: "@typescript-eslint/parser",
      plugins: ["@typescript-eslint", "prettier"],
      parserOptions: { project: ["./tsconfig.json"] },
      rules: {
        "prettier/prettier": ["warn"],
        quotes: ["warn", "double"],
        semi: ["warn", "always"],
        "import/no-named-as-default-member": 0,
        "no-useless-constructor": 0,
        "space-before-function-paren": 0,
        "no-throw-literal": 0,
        "no-new": 0,
        // Ambient `declare namespace CSS { ... }` global augmentations (CSS Custom
        // Highlight API) can't be expressed as ES modules; allow declaration-only namespaces.
        "@typescript-eslint/no-namespace": ["error", { allowDeclarations: true }],
      },
    },
  ],
};
