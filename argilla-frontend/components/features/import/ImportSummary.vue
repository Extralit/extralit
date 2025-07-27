<template>
  <div class="import-summary">
    <div class="placeholder-message">
      <h3>ImportSummary Component</h3>
      <p>This component will be implemented in task 9.1</p>
      <p>Features will include:</p>
      <ul>
        <li>Import metadata summary with statistics</li>
        <li>Detailed breakdown of results with error information</li>
        <li>Failed imports table with retry options</li>
        <li>"View Import Log" button to access detailed history</li>
        <li>"Return to Library" button for navigation</li>
      </ul>
      <div class="mock-data" v-if="summaryData.totalProcessed">
        <p><strong>Import Summary:</strong></p>
        <ul>
          <li>Total Processed: {{ summaryData.totalProcessed }}</li>
          <li>Successfully Added: {{ summaryData.successfullyAdded }}</li>
          <li>Updated: {{ summaryData.updated }}</li>
          <li>Skipped: {{ summaryData.skipped }}</li>
          <li>Failed: {{ summaryData.failed }}</li>
        </ul>
        <div v-if="summaryData.importId" class="import-id">
          <p><strong>Import ID:</strong> {{ summaryData.importId }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "ImportSummary",

  props: {
    summaryData: {
      type: Object,
      default: () => ({
        totalProcessed: 0,
        successfullyAdded: 0,
        updated: 0,
        skipped: 0,
        failed: 0,
        errors: [],
        importId: null,
      }),
    },
  },

  methods: {
    reset() {
      // Placeholder method
    },
  },
};
</script>

<style lang="scss" scoped>
.import-summary {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 300px;
}

.placeholder-message {
  text-align: center;
  padding: $base-space * 4;
  border: 2px dashed var(--border-color);
  border-radius: $border-radius;
  background: var(--bg-secondary);

  h3 {
    @include font-size(20px);
    @include line-height(30px);
    color: var(--fg-primary);
    margin-bottom: $base-space * 2;
  }

  p {
    @include font-size(14px);
    @include line-height(18px);
    color: var(--fg-secondary);
    margin-bottom: $base-space * 2;
  }

  ul {
    @include font-size(13px);
    @include line-height(18px);
    text-align: left;
    color: var(--fg-secondary);
    max-width: 400px;
    margin: 0 auto;
  }

  .mock-data {
    margin-top: $base-space * 3;
    padding: $base-space * 2;
    background: var(--bg-tertiary);
    border-radius: $border-radius-s;

    p {
      @include font-size(14px);
      @include line-height(18px);
      margin: 0 0 $base-space 0;
      color: var(--fg-primary);
      font-weight: 600;
    }

    ul {
      margin: 0 0 $base-space * 2 0;
      text-align: left;

      li {
        color: var(--fg-primary);
      }
    }

    .import-id {
      padding-top: $base-space;
      border-top: 1px solid var(--border-color);

      p {
        @include font-size(13px);
        @include line-height(18px);
        margin: 0;
        color: var(--fg-secondary);
      }
    }
  }
}
</style>
