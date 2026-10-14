<template>
  <DatasetConfigurationCard
    :item="field"
    config-type="field"
    :available-types="availableTypes"
    @is-focused="$emit('is-focused', $event)"
  >
  </DatasetConfigurationCard>
</template>

<script lang="ts">
export default {
  props: {
    field: {
      type: Object,
      required: true,
    },
    availableTypes: {
      type: Array,
      required: true,
    },
  },
  computed: {
    hasNoMapping() {
      return this.field.type.value === "no mapping";
    },
  },
  methods: {},
};
</script>
