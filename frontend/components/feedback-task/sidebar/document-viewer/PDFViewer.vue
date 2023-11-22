<template>
  <div class="pdf-container">
    <PDFView 
    :src.sync="pdfData" 
    :fileName="fileName" 
    :sidebarFeatureVisible=true 
    ref="pdfView"
    class="PDFView"
    :scale.sync="scale"
    >
      <template slot="right-toolbox">
      </template>
      <template slot="left-toolbox">
        <p class="document__title">{{ fileName }}</p>
      </template>
      <template slot="error"></template>
      <template slot="loading"></template>
    </PDFView>
  </div>
</template>

<script>
import { PDFView } from '@gabrielbu/vue-pdf-viewer';

export default {
  name: 'PDFViewerTest',
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
  },
  data() {
    return {
      scale: "0.75",
    }
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
  max-height: calc(100vh - $topbarHeight * 2); // Set maximum height to 100% of the viewport height
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
