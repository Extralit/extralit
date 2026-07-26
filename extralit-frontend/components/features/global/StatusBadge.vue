<template>
  <BaseBadge :text="label" :color="color" />
</template>

<script lang="ts">
import { computed, defineComponent } from "vue";

export const STATUS_TOKENS: Record<string, string> = {
  published: "--fg-status-submitted",
  completed: "--fg-status-submitted",
  pending: "--fg-status-pending",
  draft: "--fg-status-draft",
  discarded: "--fg-status-discarded",
};

export default defineComponent({
  name: "StatusBadge",
  props: { status: { type: String, required: true } },
  setup(props) {
    const color = computed(() => {
      const token = STATUS_TOKENS[props.status];
      return token ? `var(${token})` : "var(--fg-secondary)";
    });
    return { color };
  },
  computed: {
    label(): string {
      return this.status in STATUS_TOKENS ? this.$t(`v2Status.${this.status}`) : this.status;
    },
  },
});
</script>
