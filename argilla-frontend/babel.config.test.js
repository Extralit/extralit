module.exports = {
  presets: [
    [
      "@babel/preset-env",
      {
        targets: { node: "current" },
        modules: "commonjs",
      },
    ],
    "@babel/preset-typescript",
  ],
  plugins: [
    ["@babel/plugin-proposal-class-properties", { loose: true }],
    ["@babel/plugin-proposal-private-methods", { loose: true }],
    ["@babel/plugin-transform-runtime", { regenerator: true }],
    ["@babel/plugin-transform-private-property-in-object", { loose: true }],
  ],
};
