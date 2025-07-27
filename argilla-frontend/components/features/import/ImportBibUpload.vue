<template>
  <div class="import-bib-upload">
    <div class="placeholder-message">
      <h3>ImportBibUpload Component</h3>
      <p>This component will be implemented in task 6.1</p>
      <p>Features will include:</p>
      <ul>
        <li>Drag-and-drop .bib file upload</li>
        <li>File validation and BibTeX parsing preview</li>
        <li>Upload status and reference count display</li>
        <li>Support for Zotero, EndNote, Mendeley exports</li>
      </ul>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ImportBibUpload',

  methods: {
    reset() {
      // Placeholder method
    }
  }
}
</script>

<style lang="scss" scoped>
.import-bib-upload {
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
}
</style>