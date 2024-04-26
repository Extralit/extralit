<template>
  <div class="pdf-container">
    <PDFView 
      :src.sync="pdfData" 
      :fileName="fileName" 
      :sidebarFeatureVisible=true 
      :scale.sync="scale"
      :pageNumber="localPageNumber"
      ref="pdfView"
      class="PDFView"
    >
      <template slot="right-toolbox">
        <p class="document__title">{{ fileName }}</p>
      </template>
      <template slot="left-toolbox">
      </template>
      <template slot="error"></template>
      <template slot="loading"></template>
    </PDFView>
  </div>
</template>

<script>
import { PDFView } from '@jonnytran/vue-pdf-viewer';

export default {
  name: 'PDFViewer',
  components: {
    PDFView,
  },

  props:{
    pdfData: {
      type: Uint8Array,
      required: true,
    },
    fileName: {
      type: String,
      required: false
    },
    pageNumber: {
      type: [Number, String],
      required: false
    },
  },

  data() {
    return {
      scale: "auto",
      localPageNumber: this.pageNumber,
    }
  },
  
  mounted() {
    window.addEventListener('hashchange', this.onHashChange);
    this.onHashChange(); // Call on component mount to handle initial hash
  },

  methods: {
    onHashChange() {
      const hash = window.location.hash.substring(1); // Remove the '#' from the hash
      const [key, value] = hash.split('.');
      if (key === 'page_number' && !isNaN(value)) {
        this.localPageNumber = Number(value); 
      }
    },
  },

  errorCaptured(err, component, info) {
    this.error = err;
    console.error(`Error caught from ${component}: ${err}`);
    return false; // stops the error from propagating further
  },
  beforeUnmount() {
    this.$refs.pdfView.destroy();
    window.removeEventListener('hashchange', this.onHashChange);
  },
}
</script>

<style scoped lang="scss">
.pdf-container {
  position: relative;
  font-family: "Avenir", Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  height: 100%;
}

.PDFView {
  max-height: calc(100vh - $topbarHeight); // Set maximum height to 100% of the viewport height
  overflow-y: auto; // Enable vertical scrolling if the content exceeds the maximum height
}

.document__title {
  flex: 1;
  max-width: calc($sidebarWidth / 2);
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 600;
  margin: 0;
  padding-left: 18px;
}
</style>
