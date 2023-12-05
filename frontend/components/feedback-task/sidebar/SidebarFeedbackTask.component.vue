<template>
  <div class="sidebar__container">
    <SidebarFeedbackTaskPanel v-if="isPanelVisible" @close-panel="closePanel" :currentPanel="currentPanel">
      <HelpShortcut 
      v-if="currentPanel === 'help-shortcut'"
      />

      <FeedbackTaskProgress
      v-else-if="currentPanel === 'metrics'"
      :datasetId="datasetId"
      />

      <PDFViewer 
      v-else-if="currentPanel === 'document' && document.id !== null"
      :pdf-data="document.file_data" 
      :file-name="document.file_name"
      />

    </SidebarFeedbackTaskPanel>

    <SidebarFeedbackTask
      @on-click-sidebar-action="onClickSidebarAction"
      :sidebar-items="filteredSidebarItems"
      :active-buttons="[currentPanel, currentMode]"
      :expanded-component="currentPanel"
    />
  </div>
</template>

<script>
import "assets/icons/progress";
import "assets/icons/refresh";
import "assets/icons/shortcuts";
import useDocumentViewModel from "./document-viewer/useDocumentViewModel";

export default {
  props: {
    datasetId: {
      type: String,
      required: true,
    },
  },
  data: () => ({
    currentPanel: null,
    currentMode: "annotate",
    isPanelVisible: false,
  }),
  computed: {
    hasDocument() {
      return this.document.id !== null;
    },
    filteredSidebarItems() {
      if (!this.hasDocument) {
        let newSidebarItems = { ...this.sidebarItems };
        delete newSidebarItems.documentGroup;
        return newSidebarItems;
      }
      return this.sidebarItems;
    },
  },
  created() {
    this.sidebarItems = {
      documentGroup: {
        buttonType: "expandable",
        buttons: [
          {
            id: "document",
            tooltip: "Document Viewer",
            icon: "search",
            action: "show-document",
            type: "expandable",
            component: "PDFViewerHighlight",
          }
        ]
      },
      firstGroup: {
        buttonType: "expandable",
        buttons: [
          {
            id: "metrics",
            tooltip: "Progress",
            icon: "progress",
            action: "show-metrics",
            type: "expandable",
            component: "FeedbackTaskProgress",
          },
        ],
      },
      secondGroup: {
        buttonType: "default",
        buttons: [
          {
            id: "refresh",
            tooltip: "Refresh",
            icon: "refresh",
            group: "Refresh",
            type: "non-expandable",
            action: "refresh",
          },
        ],
      },
      bottomGroup: {
        buttonType: "expandable",
        buttons: [
          {
            id: "help-shortcut",
            tooltip: "Shortcuts",
            icon: "shortcuts",
            action: "show-help",
            type: "custom-expandable",
            component: "HelpShortcut",
          },
        ],
      },
    };
  },
  setup() {
    return useDocumentViewModel();
  },
  mounted() {
    this.$nuxt.$on('on-change-record-metadata', (metadata) => {
      if (!this.hasDocument || !metadata) { return; }

      try {
        if (metadata?.pmid != null && this.document.pmid !== metadata.pmid) {
          this.setDocumentByPubmedID(metadata.pmid);

        } else if (metadata?.doc_id != null && this.document.id !== metadata.doc_id) {
          this.setDocumentByID(metadata.doc_id);
          
        } else if (metadata?.doi != null && this.document.doi !== metadata.doi) {
          console.error('TODO set document by doi')
          // this.setDocumentByPubmedID(metadata.doi);
        }

      } catch (error) {
        console.log(error)
      } finally {
        if (this.document.id === null) {
          console.log('close panel')
          this.closePanel();
        }
      }
    });
  },
  destroyed() {
    this.$nuxt.$off('on-change-record-metadata');
  },
  methods: {
    onClickSidebarAction(group, info) {
      switch (group.toUpperCase()) {
        case "DOCUMENTGROUP":
          this.togglePanel(info);
          break;
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

      $nuxt.$emit("on-sidebar-panel", this.currentPanel);
    },
    closePanel() {
      this.isPanelVisible = false;
      this.currentPanel = null;
      $nuxt.$emit("on-sidebar-panel", null);
    },
  },
};
</script>

<style lang="scss" scoped>
.sidebar {
  &__container {
    position: fixed;
    display: flex;
    right: 0;
    z-index: 1;
    pointer-events: none;
  }
}
</style>