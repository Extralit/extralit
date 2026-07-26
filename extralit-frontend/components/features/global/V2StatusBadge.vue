<template>
  <BaseBadge :text="label" :color="color" />
</template>

<script lang="ts">
import { computed, defineComponent } from "vue";

// Semantic design-system tokens, so both themes stay correct. Every token named here MUST be
// defined in all three blocks of assets/css/themes.css (:root, [data-theme="dark"],
// [data-theme="high-contrast"]) — the spec asserts that, because a token that doesn't exist
// falls through to the var() fallback and renders every status the same grey.
//
// The badge spans two disjoint vocabularies: schema status (draft|published, /schemas) and
// v2 record status (pending|completed|discarded, V2RecordsTable). `published` and `completed`
// share --fg-status-submitted — both are the terminal "done" state, and they never appear in
// the same table, so the shared hue is not ambiguous in practice.
export const STATUS_TOKENS: Record<string, string> = {
  published: "--fg-status-submitted",
  completed: "--fg-status-submitted",
  pending: "--fg-status-pending",
  draft: "--fg-status-draft",
  discarded: "--fg-status-discarded",
};

export default defineComponent({
  name: "V2StatusBadge",
  props: { status: { type: String, required: true } },
  setup(props) {
    const color = computed(() => {
      const token = STATUS_TOKENS[props.status];
      return token ? `var(${token})` : "var(--fg-secondary)";
    });
    return { color };
  },
  computed: {
    // Unknown statuses render raw rather than as a missing-key string: this is fed straight
    // from the server, which can add a status before the frontend knows its name.
    label(): string {
      return this.status in STATUS_TOKENS ? this.$t(`v2Status.${this.status}`) : this.status;
    },
  },
});
</script>
