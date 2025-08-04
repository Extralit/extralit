import { useResolve } from "ts-injecty";
import { ref } from "vue";
import { GetFirstRecordFromHub } from "~/v1/domain/usecases/get-first-record-from-hub";
import { ImportHistoryDetails } from "~/v1/domain/entities/import/ImportHistoryDetails";
import { ImportHistoryDatasetBuilder } from "~/v1/domain/entities/import/ImportHistoryDatasetBuilder";
import { DatasetCreation } from "~/v1/domain/entities/hub/DatasetCreation";
import { MetadataCreation } from "~/v1/domain/entities/hub/MetadataCreation";

export const useDatasetConfiguration = () => {
  const firstRecord = ref(null);
  const getFirstRecordUseCase = useResolve(GetFirstRecordFromHub);

  const getFirstRecord = async (
    dataset: any,
    dataSource: "hub" | "import" = "hub",
    importData?: ImportHistoryDetails
  ) => {
    try {
      if (dataSource === "import" && importData) {
        // For ImportHistory data, use the first record from the import data
        const sampleRecord = importData.getSampleRecord();
        firstRecord.value = sampleRecord;
      } else if (dataSource === "hub") {
        // For HuggingFace Hub data, use the existing use case
        firstRecord.value = await getFirstRecordUseCase.execute(dataset);
      } else {
        // Fallback to null if no valid data source
        firstRecord.value = null;
      }
    } catch (error) {
      console.error("Error getting first record:", error);
      firstRecord.value = null;
    }
  };

  /**
   * Create a DatasetCreation instance from ImportHistory data
   * This integrates ImportHistoryDatasetBuilder for data conversion
   */
  const createDatasetFromImportHistory = (importData: ImportHistoryDetails): DatasetCreation => {
    const builder = new ImportHistoryDatasetBuilder(importData.getRawData());
    const dataset = builder.build();

    // Enhance the dataset with ImportHistory-specific metadata handling
    // Override the mappings to ensure record.metadata.reference is populated
    const originalMappings = dataset.mappings;
    Object.defineProperty(dataset, 'mappings', {
      get() {
        const mappings = { ...originalMappings };

        // Ensure we have a reference field in metadata mapping
        // This will populate record.metadata.reference from ImportHistory data
        const hasReferenceMapping = mappings.metadata.some(m => m.target === 'reference');
        if (!hasReferenceMapping && importData.fieldNames.includes('reference')) {
          mappings.metadata.push({
            source: 'reference',
            target: 'reference'
          });
        }

        return mappings;
      },
      configurable: true
    });

    return dataset;
  };

  /**
   * Configure field mapping for ImportHistory data
   * Supports ImportHistory field mapping and configuration
   */
  const configureImportHistoryFields = (
    dataset: DatasetCreation,
    importData: ImportHistoryDetails,
    fieldMappings: Array<{ source: string; target: string; type: string }>
  ) => {
    const builder = new ImportHistoryDatasetBuilder(importData.getRawData());

    // Apply field mappings to the dataset
    fieldMappings.forEach(mapping => {
      const field = dataset.fields.find(f => f.name === mapping.target);
      if (field && mapping.source !== 'no mapping') {
        // Update field configuration based on ImportHistory data
        const fieldType = builder.inferFieldType(mapping.source);
        if (fieldType !== 'no mapping') {
          // Create a new field type object since the original is read-only
          (field as any).type = { value: fieldType };
        }
      }
    });

    // Ensure metadata mappings include reference field
    const metadataField = dataset.metadata.find(m => m.name === 'reference');
    if (!metadataField && importData.fieldNames.includes('reference')) {
      const referenceMetadata = MetadataCreation.from('reference', 'terms');
      if (referenceMetadata) {
        (dataset.selectedSubset as any).metadata.push(referenceMetadata);
      }
    }
  };

  /**
   * Get suggested field mappings from ImportHistory data
   */
  const getSuggestedFieldMappings = (importData: ImportHistoryDetails) => {
    const builder = new ImportHistoryDatasetBuilder(importData.getRawData());

    return importData.fieldNames.map(fieldName => ({
      source: fieldName,
      target: fieldName,
      type: builder.inferFieldType(fieldName),
      metadataType: builder.inferMetadataType(fieldName)
    }));
  };

  /**
   * Get suggested questions from ImportHistory data
   */
  const getSuggestedQuestions = (importData: ImportHistoryDetails) => {
    const builder = new ImportHistoryDatasetBuilder(importData.getRawData());
    return builder.getSuggestedQuestions();
  };

  return {
    firstRecord,
    getFirstRecord,
    createDatasetFromImportHistory,
    configureImportHistoryFields,
    getSuggestedFieldMappings,
    getSuggestedQuestions,
  };
};
