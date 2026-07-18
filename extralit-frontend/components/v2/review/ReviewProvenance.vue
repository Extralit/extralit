<template>
  <span class="review-provenance">
    <span class="review-provenance__badge" :class="`--${source}`" v-text="$t(`review.${source}`)" />
    <template v-if="provenance">
      <span v-if="provenance.agent">{{ $t("review.agent") }}: {{ provenance.agent }}</span>
      <span v-if="provenance.score != null">{{ $t("review.score") }}: {{ provenance.score.toFixed(2) }}</span>
    </template>
  </span>
</template>

<script lang="ts">
import { type PropType } from "vue";
import { type Provenance } from "~/v2/domain/entities/review/ReferenceReview";

export default {
  name: "ReviewProvenance",
  props: {
    source: { type: String as PropType<"response" | "suggestion">, required: true },
    provenance: { type: Object as PropType<Provenance | null>, default: null },
  },
};
</script>

<style lang="scss" scoped>
.review-provenance {
  display: inline-flex;
  gap: $base-space;
  font-size: 0.8em;
  color: var(--fg-tertiary);

  &__badge {
    padding: 2px $base-space;
    border-radius: $border-radius;

    &.--suggestion {
      background: var(--bg-opacity-10);
    }

    &.--response {
      background: var(--bg-opacity-20);
    }
  }
}
</style>
