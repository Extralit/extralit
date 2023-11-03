<template>
  <div class="sidebar__container">
    <SidebarPDFPanel v-if="isPanelVisible" @close-panel="closePDFPanel">
      <div>
        <!-- {{ document.file_name }} -->
      </div>
      <!-- <PDFViewer 
        v-if="currentPanel === 'pdf'"
        :pdfUrl="pdfUrl" 
      /> -->
    </SidebarPDFPanel>

    <SidebarPDFMenu
      @on-click-sidebar-action="onClickSidebarAction"
      :sidebar-items="sidebarItems"
      :active-buttons="[currentPanel, currentMode]"
      :expanded-component="currentPanel"
    />
    
  </div>
</template>
  
<script>
import "assets/icons/shortcuts";
import { getDocument } from 'pdfjs-dist';

import useDocumentViewModel from "./sidebar-pdf-viewer/useDocumentViewModel";

export default {
  components: {
    pdf
  },
  props: {
    datasetId: {
      type: String,
      required: false,
    },
  },
  data: () => ({
    currentPanel: null,
    currentMode: "annotate",
    isPanelVisible: false
  }),
  setup() {
    return useDocumentViewModel();
  },
  created() {
    this.setDocument('11102d5f-883d-4b3f-b52b-97230a4da78e')

    this.sidebarItems = {
      firstGroup: {
        buttonType: "expandable",
        buttons: [
          {
            id: "metrics",
            tooltip: "PDF Viewer",
            icon: "search",
            action: "show-metrics",
            tooltipPosition: "right",
            type: "expandable",
            component: "FeedbackTaskProgress",
          },
        ],
      },
      secondGroup: {
        buttonType: "default",
        buttons: [
          // {
          //   id: "refresh",
          //   tooltip: "Refresh",
          //   icon: "refresh",
          //   group: "Refresh",
          //   type: "non-expandable",
          //   action: "refresh",
          // },
        ],
      },
      // bottomGroup: {
      //   buttonType: "expandable",
      //   buttons: [
      //     // {
      //     //   id: "help-shortcut",
      //     //   tooltip: "Shortcuts",
      //     //   icon: "shortcuts",
      //     //   action: "show-help",
      //     //   type: "custom-expandable",
      //     //   component: "HelpShortcut",
      //     // },
      //   ],
      // },
    };
  },
  methods: {
    onClickSidebarAction(group, info) {
      switch (group.toUpperCase()) {
        case "FIRSTGROUP":
          this.togglePanel(info);
          break;
        case "SECONDGROUP":
          this.$emit("refresh");
          break;
        case "BOTTOMGROUP":
          this.togglePanel(info);
          break;
        default:
          console.warn(info);
      }
    },
    togglePanel(panelContent) {
      this.currentPanel =
        this.currentPanel !== panelContent ? panelContent : null;

      this.isPanelVisible = !!this.currentPanel;

      $nuxt.$emit("on-sidebar-pdf-toggle-panel", this.isPanelVisible);
    },
    closePDFPanel() {
      this.isPanelVisible = false;
      this.currentPanel = null;
      $nuxt.$emit("on-sidebar-pdf-toggle-panel", null);
    },
  },
}
</script>

<style lang="scss" scoped>
.sidebar {
  &__container {
    position: fixed;
    display: flex;
    left: 0;
    z-index: 1;
    pointer-events: none;
  }
}
</style>