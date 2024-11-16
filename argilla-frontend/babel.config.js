module.exports = {
  presets: [["@babel/preset-env", { targets: { node: "current" }, loose: true }]],
  plugins: [
    ["@babel/plugin-proposal-class-properties", { loose: true }],
    ["@babel/plugin-proposal-private-methods", { loose: true }],
  ],
  env: {
    test: {
      presets: [["@babel/preset-env", { targets: { node: "current" } }], "@babel/preset-typescript"],
    },
  },
};
