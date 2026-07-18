<template>
  <div class="projection-review-form">
    <ReviewRecordCard
      v-for="record in review.records"
      :key="record.recordId"
      :record="record"
      :columns-cache="record.columnsCache"
      :errors="submitErrors[record.recordId] ?? []"
      @submit="(recordId, values) => $emit('submit', recordId, values)"
      @save-draft="(recordId, values) => $emit('save-draft', recordId, values)"
      @discard="(recordId) => $emit('discard', recordId)"
    />
  </div>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import { ReferenceReview } from "~/v2/domain/entities/review/ReferenceReview";
import ReviewRecordCard from "./ReviewRecordCard.vue";

// Pure component (spec §7): all data in via props, all effects out via emits.
// No route reads, no fetching, no queue knowledge — Phase 5's Queue UI wraps this as-is.
export default defineComponent({
  name: "ProjectionReviewForm",
  components: { ReviewRecordCard },
  props: {
    review: { type: Object as PropType<ReferenceReview>, required: true },
    submitErrors: { type: Object as PropType<Record<string, string[]>>, default: () => ({}) },
  },
  emits: ["submit", "save-draft", "discard"],
});
</script>
