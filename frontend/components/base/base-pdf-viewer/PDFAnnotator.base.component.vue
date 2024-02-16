<template>
  <div id="app">
    <pdfAnnotate 
      :toolbar="toolbar" 
      :commentWrapper="commentWrapper"
    />
  </div>
</template>

<script>
import pdfAnnotate from 'pdf-annotate-vue'
import "pdf-annotate-vue/src/css/toolbar.css";
import "pdf-annotate-vue/src/css/pdf_viewer.css";

export default {
  name: 'home',

  components: {
    pdfAnnotate
  },

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
      toolbar: true,
      commentWrapper: true,
    }
  }
}
</script>

