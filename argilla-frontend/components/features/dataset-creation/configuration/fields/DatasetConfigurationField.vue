<template>
  <DatasetConfigurationCard
    :item="field"
    config-type="field"
    :available-types="availableTypes"
    @is-focused="$emit('is-focused', $event)"
    @name-changed="updateFieldName"
  >
  </DatasetConfigurationCard>
</template>

<script>
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
  model: {
    prop: "type",
    event: "change",
  },
  methods: {
    updateFieldName(newName) {
      this.field.name = newName;
    },
  },
};
</script>
