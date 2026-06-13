<template>
  <div class="dataset-total">
    <template v-if="!!total">
      <svgicon name="records" height="12" width="12" color="var(--fg-tertiary)" aria-hidden="true" />
      <span>{{ formatNumberToK(total, 2) }} {{ $t("rows") }}</span>
    </template>
  </div>
</template>

<script>
import "assets/icons/records";
import { formatNumberToK } from "@/v1/infrastructure/services/format-number";

export default {
  props: {
    total: {
      type: Number,
      required: true,
    },
  },
  methods: {
    formatNumberToK,
  },
};
</script>

<style lang="scss" scoped>
.dataset-total {
  position: relative;
  min-height: 20px;
  display: flex;
  align-items: center;
  justify-items: flex-end;
  margin-left: auto;
  gap: calc($base-space / 2);
  color: var(--fg-tertiary);
  @include font-size(12px);
}
</style>
