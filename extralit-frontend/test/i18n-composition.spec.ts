import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { createI18n } from "vue-i18n";
import i18nConfig from "~/i18n.config";
import en from "~/translation/en";
import es from "~/translation/es";

const root = join(__dirname, "..");
const sourceDirs = ["components", "pages", "layouts", "plugins", "v1"];

const walk = (dir: string): string[] =>
  readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return walk(path);
    return /\.(vue|ts|js)$/.test(entry.name) && !/\.(spec|test)\./.test(entry.name) ? [path] : [];
  });

describe("i18n composition mode", () => {
  test("no source file calls $tc, which vue-i18n does not inject when legacy is false", () => {
    const offenders = sourceDirs
      .flatMap((dir) => walk(join(root, dir)))
      .filter((file) => /\$tc\s*\(/.test(readFileSync(file, "utf8")))
      .map((file) => relative(root, file));

    expect(offenders).toEqual([]);
  });

  test("$t with a number picks the plural form", () => {
    const { global } = createI18n({ ...i18nConfig, locale: "es", messages: { en, es } });

    expect(global.t("recordStatus.pending", 1)).toBe("pendiente");
    expect(global.t("recordStatus.pending", 2)).toBe("pendientes");
    expect(global.t("bulkAnnotation.recordsSelected", 1)).toBe("1 registro seleccionado");
    expect(global.t("bulkAnnotation.recordsSelected", 3)).toBe("3 registros seleccionados");
  });
});
