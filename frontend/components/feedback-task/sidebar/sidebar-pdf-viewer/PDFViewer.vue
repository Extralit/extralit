<template>
  <div>
    <div class="pdf-navigation">
      <div class="pdf-navigation__left">
        <div>{{ fileName }}</div>
      </div>
      <span>
        <button @click="zoomIn">+</button>
        <button @click="zoomOut">-</button>
      </span>
      <span class="pdf-navigation__right">
        <button @click="goToPreviousPage" :disabled="pdfPageNum === 1">Prev. Page</button>
        <button @click="goToNextPage" :disabled="pdfPageNum === totalPages">Next Page</button>
      </span>
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
      pdfPageNum: 1,  // Start at first page
      totalPages: 0,
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

<style scoped>
.pdf-container {
  overflow: auto;
  /* width: 100%; */
  position: relative;
  /* height: 100%; */
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
  z-index: 1;
}

.pdf-navigation {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pdf-navigation__left {
  flex: 1;
}

.pdf-navigation__right {
  display: flex;
  gap: 1rem;
}
</style>
