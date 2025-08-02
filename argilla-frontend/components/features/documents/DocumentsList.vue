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
						<BaseLoading v-if="isLoading" />
						<div v-else-if="groupedDocuments.length === 0" class="documents-list__empty">
								<p>No documents found in this workspace.</p>
						</div>
						<div v-else class="documents-list__groups">
								<div v-for="group in groupedDocuments" :key="group.reference || 'no-reference'" class="document-group">
										<div class="document-group__header">
												<h3 class="document-group__reference">
														{{ group.reference || 'No Reference' }}
												</h3>
												<div class="document-group__metadata" v-if="group.metadata">
														<BaseTag v-if="group.metadata.source" :text="group.metadata.source"
																class="metadata-tag metadata-tag--source" />
														<BaseTag v-for="collection in (group.metadata.collections || [])" :key="collection"
																:text="collection" class="metadata-tag metadata-tag--collection" />
												</div>
										</div>

										<div class="document-group__files">
												<div v-for="document in group.documents" :key="document.id" class="document-item">
														<div class="document-item__info">
																<div class="document-item__name">
																		<svgicon name="document" width="16" height="16" />
																		<span>{{ document.file_name }}</span>
																</div>
																<div class="document-item__details">
																		<span v-if="document.pmid" class="document-detail">
																				PMID: {{ document.pmid }}
																		</span>

																		<span class="document-detail">
																				Added:
																				<BaseDate format="date-relative-now" :date="document.inserted_at" />
																		</span>
																</div>
														</div>

														<div class="document-item__actions">
																<BaseButton v-if="document.url" class="document-action" @click="openDocument(document)"
																		title="View Document">
																		<svgicon name="external-link" width="14" height="14" />
																</BaseButton>
														</div>
												</div>
										</div>
								</div>
						</div>
				</div>
		</div>
</template>

<script lang="ts">
import "assets/icons/document";
import "assets/icons/external-link";

import { Document } from '~/v1/domain/entities/document/Document';
import { useDocumentsListViewModel, type DocumentGroup } from './useDocumentsListViewModel';

export default {
		name: 'DocumentsList',
		props: {
				workspaceId: {
						type: String,
						required: true,
				},
		},
		setup(props) {
				return useDocumentsListViewModel();
		},
		data() {
				return {
						documents: [] as Document[],
						isLoading: false,
				};
		},
		computed: {
				groupedDocuments(): DocumentGroup[] {
						return this.groupDocumentsByReference(this.documents);
				},

				totalFiles(): number {
						return this.documents.length;
				},
		},
		async mounted() {
				await this.fetchDocuments();
		},
		methods: {
				async fetchDocuments() {
						this.isLoading = true;
						try {
								this.documents = await this.loadDocuments(this.workspaceId);
						} catch (error) {
								console.error('Error loading documents:', error);
								// For development/testing, create some mock data to show the UI
								if (process.env.NODE_ENV === 'development') {
										this.documents = this.createMockDocuments();
								} else {
										this.$notification.error('Failed to load documents');
								}
						} finally {
								this.isLoading = false;
						}
				},

				createMockDocuments() {
						return [
								{
										id: '1',
										file_name: 'paper1.pdf',
										reference: 'Smith2023',
										pmid: '12345678',
										doi: '10.1000/example.doi.1',
										url: 'https://example.com/paper1.pdf',
										metadata: {
												source: 'bib_import',
												collections: ['Research Collection']
										},
										inserted_at: new Date().toISOString(),
										updated_at: new Date().toISOString(),
								},
								{
										id: '2',
										file_name: 'paper1_supplement.pdf',
										reference: 'Smith2023',
										pmid: '12345678',
										doi: '10.1000/example.doi.1',
										url: 'https://example.com/paper1_supplement.pdf',
										metadata: {
												source: 'bib_import',
												collections: ['Research Collection']
										},
										inserted_at: new Date().toISOString(),
										updated_at: new Date().toISOString(),
								},
								{
										id: '3',
										file_name: 'paper2.pdf',
										reference: 'Johnson2024',
										pmid: '87654321',
										doi: '10.1000/example.doi.2',
										url: 'https://example.com/paper2.pdf',
										metadata: {
												source: 'bib_import',
												collections: ['ML Papers']
										},
										inserted_at: new Date().toISOString(),
										updated_at: new Date().toISOString(),
								},
						];
				},


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
		justify-content: space-between;
		align-items: center;
		padding: $base-space * 1.5;
		border-radius: $border-radius-s;
		transition: background-color 0.2s ease;

		&:hover {
				background: var(--bg-accent-grey-1);
		}

		&__info {
				flex: 1;
		}

		&__name {
				display: flex;
				align-items: center;
				gap: $base-space;
				font-weight: 500;
				color: var(--fg-primary);
				margin-bottom: calc($base-space / 2);
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
</style>