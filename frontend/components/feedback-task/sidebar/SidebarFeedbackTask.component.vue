<template>
  <div class="sidebar__container">
    <SidebarFeedbackTaskPanel v-if="isPanelVisible" @close-panel="closePanel" :currentPanel="currentPanel">
      <HelpShortcut v-if="currentPanel === 'help-shortcut'" />

      <FeedbackTaskProgress
        v-else-if="currentPanel === 'metrics'"
        :datasetId="datasetId"
      />

      <div v-if="currentPanel === 'document'">
        <div v-if="isLoading">Loading...</div>
        <PDFViewerBaseComponent 
          v-else
          :pdf-data="document.file_data" 
          :file-name="document.file_name"
          :pageNumber="document.page_number"
        />
      </div>

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
import useDocumentViewModel from "./useDocumentViewModel.ts";

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
    metadata: null,
    isLoading: false,
  }),

  watch: {
    metadata(newMetadata, oldMetadata) {
      if ((newMetadata !== oldMetadata || !this.document) && this.currentPanel === 'document') {
        this.fetchDocument();
      }
    },
    currentPanel(newPanel, oldPanel) {
      if (newPanel === 'document' && this.metadata && (this.document.pmid !== this.metadata.pmid || this.document.id !== this.metadata.doc_id)) {
        this.fetchDocument();
      }
    },
  },

  computed: {
    documentTooltip() {
      return this.document.file_name || 'Document Viewer';
    },
    hasDocumentLoaded() {
      return this.document.id !== null;
    },
    hasDocument() {
      return this.metadata === null || this.metadata?.doc_id != null || this.metadata?.pmid != null;
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
            tooltip: this.documentTooltip, 
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
            tooltip: this.$t("sidebar.progressTooltip"),
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
            tooltip: this.$t("sidebar.refreshTooltip"),
            icon: "refresh",
            group: this.$t("refresh"),
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
            tooltip: this.$t("sidebar.shortcutsTooltip"),
            icon: "shortcuts",
            action: "show-help",
            type: "custom-expandable",
            component: "HelpShortcut",
          },
        ],
      },
    };
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
    fetchDocument() {
      this.isLoading = true;

      try {
        if (this.metadata?.pmid != null && this.document.pmid !== this.metadata.pmid) {
          this.setDocumentByPubmedID(this.metadata.pmid);
        } else if (this.metadata?.doc_id != null && this.document.id !== this.metadata.doc_id) {
          this.setDocumentByID(this.metadata.doc_id);
        } else if (!this.metadata?.pmid && !this.metadata?.doc_id && this.hasDocumentLoaded) {
          this.clearDocument();
        }

        if (this.metadata?.page_number != null) {
          this.setDocumentPageNumber(this.metadata.page_number);
        }
      } catch (error) {
        console.log(error)
      } finally {
        this.isLoading = false;
        if (!this.hasDocument) {
          this.closePanel();
        }
      }
    },
    closePanel() {
      this.isPanelVisible = false;
      this.currentPanel = null;
      $nuxt.$emit("on-sidebar-panel", null);
    },
  },

  mounted() {
    this.$nuxt.$on('on-change-record-metadata', (metadata) => {
      if (!metadata) { return; }
      this.metadata = metadata;
    });
  },

  destroyed() {
    this.$nuxt.$off('on-change-record-metadata');
  },

  setup() {
    return useDocumentViewModel();
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
    @include media("<=tablet") {
      display: none;
    }
  }
}
</style>
