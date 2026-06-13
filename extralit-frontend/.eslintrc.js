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
    "prettier/vue",
  ],
  settings: {
    "vue-i18n": {
      localeDir: "./translation/*.json",
    },
  },
  rules: {
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
      },
    },
  ],
};
