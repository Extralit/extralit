<template>
  <div class="test-import-page">
    <h1>Test Import Upload Component</h1>
    <ImportUpload @file-parsed="onFileParsed" />

    <div v-if="parsedData" class="test-results">
      <h2>Parsed Results</h2>
      <pre>{{ JSON.stringify(parsedData, null, 2) }}</pre>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TestImportPage',

  data() {
    return {
      parsedData: null
    }
  },

  methods: {
    onFileParsed(data) {
      console.log('File parsed:', data)
      this.parsedData = data
    }
  }
}
</script>

<style lang="scss" scoped>
.test-import-page {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.test-results {
  margin-top: 2rem;
  padding: 1rem;
  background: #f5f5f5;
  border-radius: 8px;

  pre {
    white-space: pre-wrap;
    word-wrap: break-word;
    font-size: 0.9rem;
    max-height: 400px;
    overflow-y: auto;
  }
}
</style>