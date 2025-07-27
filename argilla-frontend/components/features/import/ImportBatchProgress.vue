<template>
  <div class="import-batch-progress">
    <div class="placeholder-message">
      <h3>ImportBatchProgress Component</h3>
      <p>This component will be implemented in task 8.2</p>
      <p>Features will include:</p>
      <ul>
        <li>Live reloading progress bar showing overall completion</li>
        <li>Current batch status with detailed progress information</li>
        <li>Real-time status updates using job status polling</li>
        <li>Batch-by-batch progress with individual file status</li>
        <li>Cancel button to stop the upload process</li>
      </ul>
      <div class="mock-data" v-if="uploadData.totalBatches">
        <p><strong>Upload Progress:</strong></p>
        <ul>
          <li>Total Batches: {{ uploadData.totalBatches }}</li>
          <li>Current Batch: {{ uploadData.currentBatch }}</li>
          <li>Completed Jobs: {{ uploadData.completedJobs }}</li>
          <li>Failed Jobs: {{ uploadData.failedJobs }}</li>
        </ul>
      </div>
      <div v-if="isUploading" class="uploading-indicator">
        <p>Upload in progress...</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ImportBatchProgress',

  props: {
    uploadData: {
      type: Object,
      default: () => ({
        confirmedDocuments: {},
        totalBatches: 0,
        currentBatch: 0,
        jobIds: {},
        completedJobs: 0,
        failedJobs: 0
      })
    },
    isUploading: {
      type: Boolean,
      default: false
    }
  },

  methods: {
    reset() {
      // Placeholder method
    },

    cancelUpload() {
      // Placeholder method
      this.$emit('upload-cancelled')
    }
  }
}
</script>

<style lang="scss" scoped>
.import-batch-progress {
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

  .uploading-indicator {
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