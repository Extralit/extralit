import { config } from "@vue/test-utils";
import { vi } from "vitest";

// Jest set process.env.TZ = "UTC" (also enforced via vitest.config test.env).
process.env.TZ = "UTC";

// Ported verbatim from jest.setup.ts so spec expectations on translation keys hold.
const translationMock = (key: string, ...params: any[]) =>
  params.length
    ? `#${key}${params
        .map((l) => (Object.values(l).length ? Object.values(l) : l))
        .map((s) => `.${s}`)}#`
    : `#${key}#`;

vi.mock("~/v1/infrastructure/services/useTranslate", () => ({
  useTranslate: () => ({ t: translationMock, tc: translationMock }),
}));

// @vue/test-utils v2: config.mocks -> config.global.mocks
config.global.mocks = {
  $t: translationMock,
  $tc: translationMock,
  $language: { isRTL: () => false },
};

// Global directives previously registered via Vue.directive(...) / Vue.use(...).
// No-op stubs keep templates from erroring during shallow/mount.
config.global.directives = {
  "click-outside": {},
  tooltip: {},
  badge: {},
  circle: {},
  "required-field": {},
  copy: {},
};

// vue-svgicon registered <svgicon> globally; the new <svg-icon> is a component.
// Stub both names by default; specs that assert icon internals mount the real one.
config.global.stubs = {
  svgicon: true,
  "svg-icon": true,
  SvgIcon: true,
  NuxtLink: true,
};

class IntersectionObserverMock {
  root = null;
  rootMargin = "";
  thresholds = [];
  disconnect() {
    return null;
  }
  observe() {
    return null;
  }
  takeRecords() {
    return [];
  }
  unobserve() {
    return null;
  }
}
// @ts-expect-error happy-dom lacks IntersectionObserver
window.IntersectionObserver = IntersectionObserverMock;
// @ts-expect-error mirror on global
global.IntersectionObserver = IntersectionObserverMock;
