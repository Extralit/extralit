<template>
  <div class="my-progress__container">
    <TeamProgress :datasetId="datasetId" />
    <StatusCounterSkeleton v-if="!metrics.hasMetrics" class="my-progress__status--skeleton" />
    <div v-else class="my-progress__share">
      <Share v-if="canSeeShare" />
      <StatusCounter
        :ghost="true"
        :rainbow="shouldShowSubmittedAnimation"
        class="my-progress__status"
        :color="RecordStatus.submitted.color"
        :name="RecordStatus.submitted.name"
        :value="metrics.submitted"
      />
    </div>
  </div>
</template>
<script>
import { RecordStatus } from "~/v1/domain/entities/record/RecordStatus";
import { useAnnotationProgressViewModel } from "./useAnnotationProgressViewModel";

export default {
  props: {
    datasetId: {
      type: String,
      required: true,
    },
  },
  computed: {
    RecordStatus() {
      return RecordStatus;
    },
  },
  setup(props) {
    return useAnnotationProgressViewModel(props);
  },
};
</script>

<style lang="scss" scoped>
$statusCounterMinWidth: 110px;
$statusCounterMinHeight: 30px;
.my-progress {
  &__container {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-right: $base-space * 2;
  }
  &__status {
    &--skeleton {
      min-width: $statusCounterMinWidth;
      min-height: $statusCounterMinHeight;
    }
  }
  &__share {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: end;
    gap: $base-space;
  }
}
</style>
