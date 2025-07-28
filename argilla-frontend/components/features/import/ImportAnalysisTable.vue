<template>
  <div class="import-analysis-table">
    <div class="placeholder-message">
      <h3>ImportAnalysisTable Component</h3>
      <p>This component will be implemented in task 7.2</p>
      <p>Features will include:</p>
      <ul>
        <li>Tabular display using BaseSimpleTable component</li>
        <li>Columns: Reference Key, Title, Authors, Year, Import Status</li>
        <li>Toggle functionality for Add/Update/Skip selection</li>
        <li>Status indicators with color coding</li>
        <li>Save, Cancel, and Confirm Import buttons</li>
      </ul>
      <div class="mock-data" v-if="analysisData.summary">
        <p><strong>Analysis Summary:</strong></p>
        <ul>
          <li>Total: {{ analysisData.summary.total_documents }}</li>
          <li>Add: {{ analysisData.summary.add_count }}</li>
          <li>Update: {{ analysisData.summary.update_count }}</li>
          <li>Skip: {{ analysisData.summary.skip_count }}</li>
          <li>Failed: {{ analysisData.summary.failed_count }}</li>
        </ul>
      </div>
      <div v-if="loading" class="loading-indicator">
        <p>Analyzing import status...</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "ImportAnalysisTable",

  props: {
    analysisData: {
      type: Object,
      default: () => ({
        documents: {},
        summary: {
          total_documents: 0,
          add_count: 0,
          update_count: 0,
          skip_count: 0,
          failed_count: 0,
        },
      }),
    },
    loading: {
      type: Boolean,
      default: false,
    },
  },

  emits: ['update', 'retry'],

  methods: {
    reset() {
      // Placeholder method
    },
  },
};
</script>

<style lang="scss" scoped>
.import-analysis-table {
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
      margin: 0;
      text-align: left;

      li {
        color: var(--fg-primary);
      }
    }
  }

  .loading-indicator {
    margin-top: $base-space * 3;
    padding: $base-space * 2;
    background: var(--primary-color);
    color: white;
    border-radius: $border-radius-s;

    p {
      @include font-size(14px);
      @include line-height(18px);
      margin: 0;
      color: white;
    }
  }
}
</style>
