<template>
  <div class="import-pdf-upload">
    <div class="placeholder-message">
      <h3>ImportPdfUpload Component</h3>
      <p>This component will be implemented in task 6.2</p>
      <p>Features will include:</p>
      <ul>
        <li>Multiple PDF file upload with drag-and-drop</li>
        <li>File matching preview with bibliography entries</li>
        <li>Upload progress and file validation</li>
        <li>Summary status with matched/unmatched files count</li>
      </ul>
      <div class="mock-data" v-if="bibEntries.length > 0">
        <p><strong>Bibliography entries available:</strong> {{ bibEntries.length }}</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ImportPdfUpload',

  props: {
    bibEntries: {
      type: Array,
      default: () => []
    }
  },

  methods: {
    reset() {
      // Placeholder method
    }
  }
}
</script>

<style lang="scss" scoped>
.import-pdf-upload {
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
      margin: 0;
      color: var(--fg-primary);
      font-weight: 600;
    }
  }
}
</style>