process.env.TZ = "UTC";

module.exports = {
  moduleFileExtensions: ["ts", "js", "json", "vue"],
  moduleNameMapper: {
    "assets/(.*)": "<rootDir>/assets/$1",
    "^~/(.*)$": "<rootDir>/$1",
    "^~~/(.*)$": "<rootDir>/$1",
    "^@/(.*)$": "<rootDir>/$1",
    "\\.(css|less)$": "<rootDir>/__mocks__/styleMock.js",
  },
  modulePathIgnorePatterns: ["<rootDir>/e2e"],
  transform: {
    "^.+\\.js$": ["babel-jest", { configFile: './babel.config.test.js' }],
    "^.+\\.ts$": ["babel-jest", { configFile: './babel.config.test.js' }],
    ".*\\.(vue)$": "@vue/vue2-jest",
    "^.+\\.svg$": "jest-transform-stub",
  },
  transformIgnorePatterns: [
    "/node_modules/(?!(@tiptap|vue-svgicon|tabulator-tables)/)"
  ],
  snapshotSerializers: ["<rootDir>/node_modules/jest-serializer-vue"],
  testEnvironment: "jsdom",
  collectCoverageFrom: ["<rootDir>/components/**/*.vue", "<rootDir>/pages/*.vue"],
  setupFiles: ["<rootDir>/jest.setup.ts"],
  testEnvironmentOptions: {
    customExportConditions: ["node", "node-addons"],
  },
};