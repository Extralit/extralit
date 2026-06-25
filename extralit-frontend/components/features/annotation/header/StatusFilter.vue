<template>
  <RadioButtonsSelectBase
    v-if="options.length"
    class="filter-status"
    :options="options"
    :selected-option="modelValue"
    @change="onChangeOption"
    aria-label="Filter Records by Status"
    aria-controls="dropdown-menu"
  />
</template>

<script>
import { RecordStatus } from "~/v1/domain/entities/record/RecordStatus";

export default {
  props: {
    modelValue: {
      type: String,
    },
  },
  emits: ["update:modelValue"],
  data() {
    return {
      options: [
        {
          id: RecordStatus.pending.name,
          name: this.$tc(`recordStatus.${RecordStatus.pending.name}`, 1),
          color: RecordStatus.pending.color,
        },
        {
          id: RecordStatus.draft.name,
          name: this.$tc(`recordStatus.${RecordStatus.draft.name}`, 1),
          color: RecordStatus.draft.color,
        },
        {
          id: RecordStatus.discarded.name,
          name: this.$tc(`recordStatus.${RecordStatus.discarded.name}`, 1),
          color: RecordStatus.discarded.color,
        },
        {
          id: RecordStatus.valid.name,
          name: "All data",
          color: RecordStatus.valid.color,
        },
        {
          id: RecordStatus.submitted.name,
          name: this.$tc(`recordStatus.${RecordStatus.submitted.name}`, 1),
          color: RecordStatus.submitted.color,
        },
      ],
    };
  },
  methods: {
    onChangeOption(option) {
      this.$emit("update:modelValue", option);
    },
  },
};
</script>

<style lang="scss" scoped>
.filter-status {
  flex-shrink: 0;
}
</style>
