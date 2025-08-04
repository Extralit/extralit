/**
 * Builder class for converting ImportHistory data to DatasetCreation format
 * Handles field mapping and data type inference similar to HuggingFace datasets
 */

import { DatasetCreation } from "../hub/DatasetCreation";
import { Subset } from "../hub/Subset";
import { FieldCreationTypes } from "../hub/FieldCreation";
import { MetadataTypes } from "../hub/MetadataCreation";
import { ImportHistoryDetailsResponse } from "../../usecases/get-import-history-details-use-case";

export interface ImportHistoryFeature {
  dtype: "string" | "int32" | "int64" | "float32" | "boolean";
  _type: "Value";
  name: string;
}

export class ImportHistoryDatasetBuilder {
  private readonly importHistoryData: ImportHistoryDetailsResponse;
  private readonly datasetName: string;

  constructor(importHistoryData: ImportHistoryDetailsResponse) {
    this.importHistoryData = importHistoryData;
    this.datasetName = this.generateDatasetName();
  }

  build(): DatasetCreation {
    const subset = this.createSubsetFromImportHistory();
    const dataset = new DatasetCreation(this.importHistoryData.id, this.datasetName, [subset]);

    // Enhance the dataset to ensure proper reference field handling
    this.enhanceDatasetForImportHistory(dataset);

    return dataset;
  }

  /**
   * Enhance DatasetCreation instance for ImportHistory-specific requirements
   */
  private enhanceDatasetForImportHistory(dataset: DatasetCreation): void {
    // Override the mappings getter to ensure reference field is included in metadata
    const originalMappings = dataset.mappings;

    Object.defineProperty(dataset, "mappings", {
      get: () => {
        const mappings = {
          fields: originalMappings.fields,
          metadata: [...originalMappings.metadata],
          suggestions: originalMappings.suggestions,
          external_id: originalMappings.external_id,
        };

        // Ensure reference field is mapped to metadata if it exists
        if (this.hasReferenceField()) {
          const hasReferenceMapping = mappings.metadata.some((m) => m.target === "reference");
          if (!hasReferenceMapping) {
            // Add reference field to metadata mapping
            const referenceSource = this.availableFields.includes("reference")
              ? "reference"
              : this.availableFields.includes("id")
              ? "id"
              : null;

            if (referenceSource) {
              mappings.metadata.push({
                source: referenceSource,
                target: "reference",
              });
            }
          }
        }

        return mappings;
      },
      configurable: true,
      enumerable: true,
    });

    // Override createFields to ensure proper field creation with ImportHistory data
    const originalCreateFields = dataset.createFields.bind(dataset);
    dataset.createFields = (firstRawRecord: unknown) => {
      // Use ImportHistory first record if no record provided
      const recordToUse = firstRawRecord || this.firstRecord;
      return originalCreateFields(recordToUse);
    };
  }

  private generateDatasetName(): string {
    // Generate dataset name from filename, removing extension and making it dataset-friendly
    const baseName = this.importHistoryData.filename
      .replace(/\.[^/.]+$/, "") // Remove file extension
      .replace(/[^a-zA-Z0-9_-]/g, "_") // Replace special chars with underscore
      .toLowerCase();

    return `${baseName}_dataset`;
  }

  private createSubsetFromImportHistory(): Subset {
    // Create a mock datasetInfo structure that mimics HuggingFace format
    const features = this.extractFeaturesFromSchema();

    // Ensure reference field is included in features if it exists in the data
    if (this.hasReferenceField() && !features.reference) {
      features.reference = {
        dtype: "string",
        _type: "Value",
        name: "reference",
      };
    }

    const mockDatasetInfo = {
      default: {
        dataset_name: this.datasetName,
        features,
        splits: {
          train: {
            name: "train",
            num_bytes: 0,
            num_examples: this.importHistoryData.data.data.length,
          },
        },
      },
    };

    return new Subset("default", mockDatasetInfo.default);
  }

  /**
   * Check if the ImportHistory data contains a reference field
   */
  private hasReferenceField(): boolean {
    return (
      this.importHistoryData.data.schema.fields.some((field) => field.name === "reference" || field.name === "id") ||
      this.importHistoryData.data.data.some((record) => "reference" in record || "id" in record)
    );
  }

  private extractFeaturesFromSchema(): Record<string, ImportHistoryFeature> {
    const features: Record<string, ImportHistoryFeature> = {};

    // Process each field from the ImportHistory schema
    this.importHistoryData.data.schema.fields.forEach((field) => {
      features[field.name] = {
        dtype: this.mapDataTypeToFeatureType(field.type),
        _type: "Value",
        name: field.name,
      };
    });

    return features;
  }

  private mapDataTypeToFeatureType(dataType: string): "string" | "int32" | "int64" | "float32" | "boolean" {
    // Map ImportHistory data types to feature types
    switch (dataType.toLowerCase()) {
      case "string":
      case "text":
        return "string";
      case "integer":
      case "int":
      case "int32":
        return "int32";
      case "int64":
      case "bigint":
        return "int64";
      case "float":
      case "float32":
      case "double":
        return "float32";
      case "boolean":
      case "bool":
        return "boolean";
      default:
        // Default to string for unknown types
        return "string";
    }
  }

  /**
   * Get the first record from ImportHistory data for field mapping
   * This is used by DatasetConfiguration to populate field examples
   */
  get firstRecord(): Record<string, any> {
    if (this.importHistoryData.data.data.length === 0) {
      return {};
    }
    return this.importHistoryData.data.data[0];
  }

  /**
   * Get records with enhanced metadata including reference field
   * Ensures record.metadata.reference is populated from ImportHistory data
   */
  getRecordsWithMetadata(): Array<Record<string, any> & { metadata: { reference?: string } }> {
    return this.importHistoryData.data.data.map((record) => ({
      ...record,
      metadata: {
        ...record.metadata,
        reference: record.reference || record.id || `record_${Math.random().toString(36).substr(2, 9)}`,
      },
    }));
  }

  /**
   * Get all data records from ImportHistory
   * This is used for preview and dataset creation
   */
  get allRecords(): Record<string, any>[] {
    return this.importHistoryData.data.data;
  }

  /**
   * Get field names available for mapping
   */
  get availableFields(): string[] {
    return this.importHistoryData.data.schema.fields.map((field) => field.name);
  }

  /**
   * Infer field type for DatasetConfiguration field mapping
   */
  inferFieldType(fieldName: string): FieldCreationTypes {
    const field = this.importHistoryData.data.schema.fields.find((f) => f.name === fieldName);
    if (!field) return "no mapping";

    // Map data types to field creation types
    switch (field.type.toLowerCase()) {
      case "string":
      case "text":
        // Check if this looks like a text field that should be used for annotation
        if (this.isTextAnnotationField(fieldName)) {
          return "text";
        }
        return "no mapping"; // Most string fields will be metadata
      default:
        return "no mapping"; // Non-text fields typically become metadata
    }
  }

  /**
   * Infer metadata type for DatasetConfiguration metadata mapping
   */
  inferMetadataType(fieldName: string): MetadataTypes | "terms" | null {
    const field = this.importHistoryData.data.schema.fields.find((f) => f.name === fieldName);
    if (!field) return null;

    // Map data types to metadata types
    switch (field.type.toLowerCase()) {
      case "integer":
      case "int":
      case "int32":
        return "int32";
      case "int64":
      case "bigint":
        return "int64";
      case "float":
      case "float32":
      case "double":
        return "float32";
      default:
        return "terms"; // String fields become terms metadata
    }
  }

  /**
   * Check if a field should be treated as a text annotation field
   */
  private isTextAnnotationField(fieldName: string): boolean {
    const textFieldNames = [
      "title",
      "abstract",
      "content",
      "text",
      "description",
      "summary",
      "body",
      "article",
      "document",
    ];

    return textFieldNames.some((name) => fieldName.toLowerCase().includes(name.toLowerCase()));
  }

  /**
   * Get suggested question mappings based on field names
   */
  getSuggestedQuestions(): Array<{
    fieldName: string;
    questionName: string;
    questionType: "label_selection" | "multi_label_selection" | "text" | "rating";
    options?: Array<{ text: string; value: string; id: string }>;
  }> {
    const suggestions: Array<{
      fieldName: string;
      questionName: string;
      questionType: "label_selection" | "multi_label_selection" | "text" | "rating";
      options?: Array<{ text: string; value: string; id: string }>;
    }> = [];

    // Look for fields that might be good for questions
    this.availableFields.forEach((fieldName) => {
      const lowerName = fieldName.toLowerCase();

      // Suggest text questions for abstract/title fields
      if (lowerName.includes("abstract") || lowerName.includes("summary")) {
        suggestions.push({
          fieldName,
          questionName: `${fieldName}_quality`,
          questionType: "rating",
        });
      }

      // Suggest label selection for categorical fields
      if (lowerName.includes("category") || lowerName.includes("type") || lowerName.includes("status")) {
        suggestions.push({
          fieldName,
          questionName: `${fieldName}_classification`,
          questionType: "label_selection",
          options: [
            { text: "Relevant", value: "relevant", id: "relevant" },
            { text: "Not Relevant", value: "not_relevant", id: "not_relevant" },
          ],
        });
      }
    });

    return suggestions;
  }
}
