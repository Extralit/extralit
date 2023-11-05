<template>
  <div>
    <canvas ref="pdfCanvas"></canvas>
    <button @click="goToPreviousPage" :disabled="pdfPageNum === 1">Previous</button>
    <button @click="goToNextPage" :disabled="pdfPageNum === totalPages">Next</button>
  </div>
</template>

<script>
import { getDocument } from 'pdfjs-dist';

export default {
  name: 'PDFViewer',
  props: {
    pdfData: {
      type: Uint8Array,
      required: true,
    },
  },
  data() {
    return {
      pdfDocument: null,
      pdfPageNum: 1,  // Start at first page
      totalPages: 0,
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
        const canvas = this.$refs.pdfCanvas;
        const context = canvas.getContext('2d');
        const viewport = page.getViewport({ scale: 1.5 });
        canvas.height = viewport.height;
        canvas.width = viewport.width;
        const renderContext = {
          canvasContext: context,
          viewport: viewport,
        };
          await page.render(renderContext).promise;
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
  },
  mounted() {
    this.loadPdf();
  },
  watch: {
    pdfData: 'loadPdf',
  },
};
</script>
