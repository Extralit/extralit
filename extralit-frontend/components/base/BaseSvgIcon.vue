<template>
  <span class="svg-icon" :data-icon="name" v-html="svg" />
</template>

<script setup lang="ts">
import { computed } from "vue";

/**
 * Drop-in replacement for vue-svgicon's `<svgicon>` (registered globally under
 * the same names in plugins/svg-icon.ts). Reads the raw SVG source files from
 * `static/icons` at build time and applies the width/height/color props by
 * rewriting the `<svg>` markup, preserving the original call signature.
 */
const props = withDefaults(
  defineProps<{
    name: string;
    width?: number | string;
    height?: number | string;
    color?: string;
  }>(),
  {}
);

const modules = import.meta.glob("~/static/icons/**/*.svg", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

const toCssSize = (value?: number | string): string | undefined => {
  if (value == null) return undefined;
  if (typeof value === "number") return `${value}px`;
  return /^\d+(\.\d+)?$/.test(value) ? `${value}px` : value;
};

const raw = computed(() => {
  const hit = Object.entries(modules).find(([path]) => path.endsWith(`/${props.name}.svg`));
  return hit ? hit[1] : "";
});

const svg = computed(() => {
  let markup = raw.value;
  if (!markup) return "";

  const width = toCssSize(props.width);
  const height = toCssSize(props.height);

  // Strip the intrinsic width/height off the root <svg> so ours win (viewBox
  // keeps the aspect ratio), then inject the requested dimensions.
  markup = markup
    .replace(/(<svg\b[^>]*?)\swidth="[^"]*"/i, "$1")
    .replace(/(<svg\b[^>]*?)\sheight="[^"]*"/i, "$1");
  const sized: string[] = [];
  if (width) sized.push(`width="${width}"`);
  if (height) sized.push(`height="${height}"`);
  if (sized.length) markup = markup.replace(/<svg\b/i, `<svg ${sized.join(" ")}`);

  // vue-svgicon's `color` prop recolored the icon; mirror that for the common
  // monochrome icons (black fills) when a color is supplied.
  if (props.color) {
    markup = markup.replace(/fill="(?:black|#000|#000000)"/gi, `fill="${props.color}"`);
  }

  return markup;
});
</script>

<style lang="scss" scoped>
.svg-icon {
  display: inline-flex;
  line-height: 0;
}
</style>
