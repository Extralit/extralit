<template>
  <div class="documents-list">
    <div class="documents-list__header">
      <h2 class="documents-list__title">Documents</h2>
      <div class="documents-list__stats">
        <span class="stat-item">
          <span class="stat-label">Total References:</span>
          <span class="stat-value">{{ groupedDocuments.length }}</span>
        </span>
        <span class="stat-item">
          <span class="stat-label">Total Files:</span>
          <span class="stat-value">{{ totalFiles }}</span>
        </span>
      </div>
    </div>
    <div class="documents-list__content">
      <div v-if="groupedDocuments.length === 0" class="documents-list__empty">
        <p>No documents found in this workspace.</p>
      </div>
      <div v-else class="documents-list__groups">
        <div v-for="group in groupedDocuments" :key="group.reference || 'no-reference'" class="document-group">
          <div class="document-group__header">
            <h3 class="document-group__reference">
              {{ group.reference || "No Reference" }}
            </h3>
            <div class="document-group__metadata" v-if="group.metadata">
              <BaseTag
                v-if="group.metadata.source"
                :name="group.metadata.source"
                class="metadata-tag metadata-tag--source"
              />
              <BaseTag
                v-for="collection in group.metadata.collections || []"
                :key="collection"
                :name="collection"
                class="metadata-tag metadata-tag--collection"
              />
            </div>
          </div>

          <div class="document-group__files">
            <div v-for="document in group.documents" :key="document.id" class="document-item">
              <div class="document-item__thumbnail">
                <img
                  v-if="document.thumbnail_url"
                  :src="document.thumbnail_url"
                  :alt="`Thumbnail for ${document.file_name}`"
                  class="thumbnail-image"
                  loading="lazy"
                  @error="onThumbnailError"
                />
                <div v-else class="thumbnail-placeholder">
                  <svgicon name="document" width="24" height="24" />
                </div>
              </div>

              <div class="document-item__info">
                <div class="document-item__name">
                  <span>{{ document.file_name }}</span>
                </div>
                <div class="document-item__details">
                  <span v-if="document.pmid" class="document-detail"> PMID: {{ document.pmid }} </span>

                  <span class="document-detail">
                    Added:
                    <BaseDate format="date-relative-now" :date="document.inserted_at" />
                  </span>
                </div>
              </div>

              <div class="document-item__actions">
                <BaseButton
                  v-if="document.metadata"
                  class="document-action"
                  @on-click="showDocumentMetadata(document)"
                  title="View Metadata"
                >
                  <svgicon name="info" width="14" height="14" />
                </BaseButton>
                <BaseButton
                  v-if="document.url"
                  class="document-action"
                  @on-click="openDocument(document)"
                  title="View Document"
                >
                  <svgicon name="external-link" width="14" height="14" />
                </BaseButton>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Metadata Modal -->
    <BaseModal
      v-if="showMetadataModal"
      :modal-visible="showMetadataModal"
      :modal-title="selectedDocumentName"
      modal-class="modal-auto"
      @close-modal="closeMetadataModal"
    >
      <div class="metadata-content">
        <pre class="metadata-json">
          <template v-if="!selectedDocumentMetadata?.text_extraction_metadata?.markdown">{{ JSON.stringify(selectedDocumentMetadata, null, 2) }}
          </template>
          <MarkdownRenderer
            v-if-else="selectedDocumentMetadata?.text_extraction_metadata?.markdown"
            :markdown="selectedDocumentMetadata?.text_extraction_metadata?.markdown || ''"
          />
        </pre>
      </div>
    </BaseModal>
  </div>
</template>

<script lang="ts">

import { useDocumentsListViewModel } from "./useDocumentsListViewModel";

export default {
  name: "DocumentsList",
  props: {
    workspaceId: {
      type: String,
      required: true,
    },
  },
  setup(props) {
    return useDocumentsListViewModel(props);
  },
};
</script>

<style lang="scss" scoped>
.documents-list {
  padding: $base-space * 2;

  &__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: $base-space * 3;
    padding-bottom: $base-space * 2;
    border-bottom: 1px solid var(--bg-opacity-6);
  }

  &__title {
    margin: 0;
    font-size: 24px;
    font-weight: 500;
    color: var(--fg-primary);
  }

  &__stats {
    display: flex;
    gap: $base-space * 2;

    .stat-item {
      display: flex;
      align-items: center;
      gap: $base-space;
      font-size: 14px;

      .stat-label {
        color: var(--fg-secondary);
      }

      .stat-value {
        font-weight: 500;
        color: var(--fg-primary);
      }
    }
  }

  &__empty {
    text-align: center;
    padding: $base-space * 4;
    color: var(--fg-tertiary);
  }

  &__groups {
    display: flex;
    flex-direction: column;
    gap: $base-space * 3;
  }
}

.document-group {
  border: 1px solid var(--bg-opacity-6);
  border-radius: $border-radius-m;
  overflow: hidden;

  &__header {
    background: var(--bg-accent-grey-3);
    padding: $base-space * 2;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  &__reference {
    margin: 0;
    font-size: 16px;
    font-weight: 500;
    color: var(--fg-primary);
  }

  &__metadata {
    display: flex;
    gap: $base-space;
    flex-wrap: wrap;
  }

  &__files {
    padding: $base-space;
  }
}

.metadata-tag {
  font-size: 12px;

  &--source {
    background: var(--bg-accent-blue-1);
    color: var(--fg-accent-blue);
  }

  &--collection {
    background: var(--bg-accent-green-1);
    color: var(--fg-accent-green);
  }
}

.document-item {
  display: flex;
  align-items: center;
  padding: $base-space * 1.5;
  border-radius: $border-radius-s;
  transition: background-color 0.2s ease;
  gap: $base-space * 1.5;

  &:hover {
    background: var(--bg-accent-grey-1);
  }

  &__thumbnail {
    flex-shrink: 0;
    width: 60px;
    height: 80px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-accent-grey-2);
    border: 1px solid var(--bg-opacity-6);
    border-radius: $border-radius-s;
    overflow: hidden;

    .thumbnail-image {
      width: 100%;
      height: 100%;
      object-fit: cover;
      object-position: top;
    }

    .thumbnail-placeholder {
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--fg-tertiary);
      width: 100%;
      height: 100%;
    }
  }

  &__info {
    flex: 1;
    min-width: 0; // Allow shrinking and text truncation
  }

  &__name {
    display: flex;
    align-items: center;
    gap: $base-space;
    font-weight: 500;
    color: var(--fg-primary);
    margin-bottom: calc($base-space / 2);
    white-space: normal; // allow wrapping
    word-break: break-word; // break long words if needed
    flex: 0 1 auto; // allow shrinking and wrapping
  }

  &__details {
    display: flex;
    gap: $base-space * 2;
    font-size: 12px;
    color: var(--fg-secondary);
  }

  &__actions {
    display: flex;
    gap: $base-space;
    flex-shrink: 0;
  }
}

.document-action {
  &.button {
    padding: calc($base-space/2);
    color: var(--fg-tertiary);

    &:hover {
      color: var(--fg-secondary);
    }
  }
}

.metadata-content {
  max-height: 80vh;
  max-width: 90vw;
  overflow-y: auto;

  .metadata-json {
    background: var(--bg-accent-grey-2);
    border: 1px solid var(--bg-opacity-6);
    border-radius: $border-radius-s;
    padding: $base-space * 2;
    margin: 0;
    font-size: 12px;
    line-height: 1.4;
    color: var(--fg-primary);
    white-space: pre-wrap;
    word-break: break-all;
  }
}
</style>
