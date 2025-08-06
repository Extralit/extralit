module.exports = {
  presets: [["@babel/preset-env", { targets: { node: "current" }, loose: true }]],
  plugins: [
    ["@babel/plugin-transform-class-properties", { loose: true }],
    ["@babel/plugin-transform-private-methods", { loose: true }],
    ["@babel/plugin-transform-private-property-in-object", { loose: true }],
  ],
  env: {
    test: {
      presets: [["@babel/preset-env", { targets: { node: "current" }, loose: true }], "@babel/preset-typescript"],
    },
  },
};
