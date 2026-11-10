import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";

const root = join(__dirname, "..");
const sourceDirs = ["components", "pages", "layouts"];

const walk = (dir: string): string[] =>
  readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return walk(path);
    return entry.name.endsWith(".vue") ? [path] : [];
  });

describe("SFC script blocks", () => {
  test("no SFC pairs <script setup> with an options-API setup(), which Vue silently ignores", () => {
    const offenders = sourceDirs
      .flatMap((dir) => walk(join(root, dir)))
      .filter((file) => {
        const source = readFileSync(file, "utf8");
        return /<script[^>]*\bsetup\b[^>]*>/.test(source) && /^\s*setup\s*\(/m.test(source);
      })
      .map((file) => relative(root, file));

    expect(offenders).toEqual([]);
  });
});
