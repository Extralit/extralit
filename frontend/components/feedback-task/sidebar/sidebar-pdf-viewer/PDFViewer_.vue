<template>
  <div>
    <div class="pdf-navigation">
      <div class="title-container">
        <p class="document__title">{{ fileName }}</p>
      </div>
      <div class="controls">
        <div class="zoom-controls">
          <button @click="zoomOut">-</button>
          <button @click="zoomIn">+</button>
        </div>
        <div class="page-controls">
          <button @click="goToPreviousPage" :disabled="pdfPageNum === 1">Prev. Page</button>
          <button @click="goToNextPage" :disabled="pdfPageNum === totalPages">Next Page</button>
        </div>
      </div>
    </div>
    
    <div ref="pdfContainer" class="pdf-container">
      <canvas ref="pdfCanvas" class="pdf-canvas"></canvas>
      <div ref="textLayer" class="textLayer"></div>
    </div>
  </div>
</template>

<script>
import BaseButton from "@/components/base/base-button/BaseButton.vue";
import { getDocument, PDFPageProxy, renderTextLayer } from 'pdfjs-dist';
import 'pdfjs-dist/web/pdf_viewer.css'

export default {
  name: 'PDFViewer',
  props: {
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
      pdfDocument: null,
      pdfPage: null,
      totalPages: null,
      pdfPageNum: 1,  // Start at first page
      scale: 1,
    };
  },
  methods: {
    async loadPdf() {
      try {
        const loadingTask = getDocument({ data: this.pdfData });
        this.pdfDocument = await loadingTask.promise;
        this.totalPages = this.pdfDocument.numPages;
        this.renderPage(this.pdfPageNum);
      } catch (error) {
        console.error('Error loading PDF:', error);
      }
    },
    async renderPage(num) {
      try {
        const page = await this.pdfDocument.getPage(num);
        const pdfContainer = this.$refs.pdfContainer;
        const canvas = this.$refs.pdfCanvas;
        const context = canvas.getContext('2d');
        const viewport = page.getViewport({ scale: this.scale });
        canvas.width = viewport.width;
        canvas.height = viewport.height;

        // Render PDF page
        await page.render({
          canvasContext: context,
          viewport,
        }).promise;

        // Render text layer
        const textLayer = this.$refs.textLayer;
        if (textLayer) {  // Check if textLayer is defined
          textLayer.innerHTML = '';  // Clear previous text layer if any
          textLayer.style.width = `${viewport.width}px`;
          textLayer.style.height = `${viewport.height}px`;

          const textContent = await page.getTextContent();
          renderTextLayer({
            textContent,
            container: textLayer,
            viewport,
            textDivs: [],
          });
        } else {
          console.error('textLayer ref is undefined');
        }
      } catch (error) {
        console.error('Error rendering page:', error);
      }
    },
    goToPreviousPage() {
      if (this.pdfPageNum > 1) {
        this.pdfPageNum--;
        this.renderPage(this.pdfPageNum);
      }
    },
    goToNextPage() {
      if (this.pdfPageNum < this.totalPages) {
        this.pdfPageNum++;
        this.renderPage(this.pdfPageNum);
      }
    },
    zoomIn() {
      this.scale *= 1.1;  // adjust factor as necessary
      this.renderPage(this.pdfPageNum);
    },
    zoomReset() {
      this.scale = 1;
      this.renderPage(this.pdfPageNum);
    },
    zoomOut() {
      this.scale /= 1.1;  // adjust factor as necessary
      this.renderPage(this.pdfPageNum);
    },
  },
  mounted() {
    this.loadPdf();
  },
  watch: {
    pdfData: 'loadPdf',
  },
};
</script>

<style lang="scss" scoped>
.pdf-navigation {
  display: flex;
  flex-direction: row; 
  align-items: center; 
  justify-content: space-between;
  margin-bottom: 16px; 
}

.title-container {
  flex: 1;
  max-width: calc(100% - 200px); 
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  padding: 5px;
}

.document__title {
  white-space: nowrap;
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.controls {
  display: flex;
  gap: 8px;
}

.zoom-controls,
.page-controls {
  display: flex;
  gap: 8px;
}

.pdf-container {
  all: initial;
  overflow-x: auto;
  overflow-y: auto;
  position: relative;
}

.pdf-canvas {
  display: block;
  /* min-width: 100%; */
}

.pdf-canvas, .textLayer {
  /* position: absolute; */
  left: 0;
  top: 0;
  pointer-events: none;
}

.textLayer {
  z-index: 10;
}
</style>
