/**
 * Use case for bulk document upload with sequential batch processing
 */

import { type NuxtAxiosInstance } from "@nuxtjs/axios";
import type { DocumentMetadata } from "~/v1/domain/entities/import/ImportAnalysis";

// Bulk upload request structure
export interface BulkDocumentInfo {
  reference: string;
  document_create: any; // DocumentCreate from backend
  associated_files: string[]; // Multiple PDF filenames for this reference
}

export interface DocumentsBulkCreate {
  documents: BulkDocumentInfo[];
}

export interface DocumentsBulkResponse {
  job_ids: Record<string, string>; // Reference to job_id mapping
  total_documents: number;
  failed_validations: string[];
}

export class BulkUploadDocumentsUseCase {
  constructor(private readonly axios: NuxtAxiosInstance) { }

  async execute(
    confirmedDocuments: Record<string, DocumentMetadata>,
    files: File[]
  ): Promise<DocumentsBulkResponse> {
    // Create file mapping for quick lookup
    const fileMapping = new Map<string, File>();
    files.forEach(file => {
      fileMapping.set(file.name, file);
    });

    // Convert confirmed documents to bulk upload format
    const bulkDocuments: BulkDocumentInfo[] = [];

    for (const [reference, docMetadata] of Object.entries(confirmedDocuments)) {
      bulkDocuments.push({
        reference,
        document_create: docMetadata.document_create,
        associated_files: docMetadata.associated_files.map(f => f.filename),
      });
    }

    // Check if there are any documents to upload
    if (bulkDocuments.length === 0) {
      return {
        job_ids: {},
        total_documents: 0,
        failed_validations: ["No documents to upload"]
      };
    }

    const bulkCreate: DocumentsBulkCreate = {
      documents: bulkDocuments,
    };

    // Prepare form data
    const formData = new FormData();
    formData.append("documents_metadata", JSON.stringify(bulkCreate));

    // Add all referenced files to form data
    const addedFiles = new Set<string>();
    const missingFiles: string[] = [];

    for (const doc of bulkDocuments) {
      for (const filename of doc.associated_files) {
        if (!addedFiles.has(filename)) {
          const file = fileMapping.get(filename);
          if (file) {
            formData.append("files", file);
            addedFiles.add(filename);
          } else {
            missingFiles.push(filename);
          }
        }
      }
    }

    // Log warning if no files are being uploaded
    if (addedFiles.size === 0) {
      console.warn("No files found for upload. Uploading documents without associated files.");
    }

    // Report missing files as validation errors
    const failed_validations: string[] = [];
    if (missingFiles.length > 0) {
      failed_validations.push(`Missing files: ${missingFiles.join(", ")}`);
    }

    try {
      // Send bulk upload request
      const response = await this.axios.post<DocumentsBulkResponse>(
      "/v1/documents/bulk",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
          timeout: 300000, // 5 minute timeout for large uploads
        }
      );

      // Merge any pre-upload validation errors with backend response
      const result = response.data;
      if (failed_validations.length > 0) {
        result.failed_validations = [...result.failed_validations, ...failed_validations];
      }

      return result;
    } catch (error: any) {
      // If we have validation errors and the request fails, include them in the error
      if (failed_validations.length > 0) {
        throw new Error(`Upload failed with validation errors: ${failed_validations.join(", ")}. ${error.message || error}`);
      }
      throw error;
    }
  }
}