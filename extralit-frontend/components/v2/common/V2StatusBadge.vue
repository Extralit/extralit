<template>
  <BaseBadge :text="status" :color="color" />
</template>

<script lang="ts">
import { computed, defineComponent } from "vue";

// Token colors reused from the design system's semantic vars so both themes stay correct.
const STATUS_COLORS: Record<string, string> = {
  published: "var(--fg-status-active, var(--fg-secondary))",
  completed: "var(--fg-status-active, var(--fg-secondary))",
  pending: "var(--fg-tertiary)",
  discarded: "var(--fg-status-danger, var(--fg-tertiary))",
  draft: "var(--fg-tertiary)",
};

export default defineComponent({
  name: "V2StatusBadge",
  props: { status: { type: String, required: true } },
  setup(props) {
    const color = computed(() => STATUS_COLORS[props.status] ?? "var(--fg-secondary)");
    return { color };
  },
});
</script>
