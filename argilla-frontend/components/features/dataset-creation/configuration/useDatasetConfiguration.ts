import { useResolve } from "ts-injecty";
import { ref } from "vue";
import { GetFirstRecordFromHub } from "~/v1/domain/usecases/get-first-record-from-hub";
import { ImportHistoryDetails } from "~/v1/domain/entities/import/ImportHistoryDetails";
import { ImportHistoryDatasetBuilder } from "~/v1/domain/entities/import/ImportHistoryDatasetBuilder";
import { DatasetCreation } from "~/v1/domain/entities/hub/DatasetCreation";
import { MetadataCreation } from "~/v1/domain/entities/hub/MetadataCreation";
import { FieldType } from "~/v1/domain/entities/field/FieldType";

export const useDatasetConfiguration = () => {
  const firstRecord = ref(null);
  const getFirstRecordUseCase = useResolve(GetFirstRecordFromHub);

  const getFirstRecord = async (
    dataset: any,
    dataSource: "hub" | "import" = "hub",
    importData?: ImportHistoryDetails | any
  ) => {
    try {
      if (dataSource === "import" && importData) {
        // Handle both ImportHistoryDetails instance and raw data
        let sampleRecord;

        if (importData.getSampleRecord && typeof importData.getSampleRecord === 'function') {
          // It's an ImportHistoryDetails instance
          sampleRecord = importData.getSampleRecord();
        } else if (importData.data && importData.data.data && importData.data.data.length > 0) {
          // It's raw ImportHistoryDetailsResponse data
          sampleRecord = importData.data.data[0];
        } else {
          // Fallback - try to find data in various possible structures
          sampleRecord = null;
        }

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
  const createDatasetFromImportHistory = (importData: ImportHistoryDetails | any): DatasetCreation => {
    // Handle both ImportHistoryDetails instance and raw data
    let rawData;
    let fieldNames: string[] = [];

    if (importData.getRawData && typeof importData.getRawData === 'function') {
      // It's an ImportHistoryDetails instance
      rawData = importData.getRawData();
      fieldNames = importData.fieldNames || [];
    } else {
      // It's raw ImportHistoryDetailsResponse data
      rawData = importData;
      fieldNames = importData.data?.schema?.fields?.map((f: any) => f.name) || [];
    }

    const builder = new ImportHistoryDatasetBuilder(rawData);
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
        if (!hasReferenceMapping && fieldNames.includes('reference')) {
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
    importData: ImportHistoryDetails | any,
    fieldMappings: Array<{ source: string; target: string; type: string }>
  ) => {
    // Handle both ImportHistoryDetails instance and raw data
    let rawData;
    let fieldNames: string[] = [];

    if (importData.getRawData && typeof importData.getRawData === 'function') {
      // It's an ImportHistoryDetails instance
      rawData = importData.getRawData();
      fieldNames = importData.fieldNames || [];
    } else {
      // It's raw ImportHistoryDetailsResponse data
      rawData = importData;
      fieldNames = importData.data?.schema?.fields?.map((f: any) => f.name) || [];
    }

    const builder = new ImportHistoryDatasetBuilder(rawData);

    // Apply field mappings to the dataset
    fieldMappings.forEach(mapping => {
      const field = dataset.fields.find(f => f.name === mapping.target);
      if (field && mapping.source !== 'no mapping') {
        // Update field configuration based on ImportHistory data
        const fieldType = builder.inferFieldType(mapping.source);
        if (fieldType !== 'no mapping') {
          // Set the field type as a FieldType instance
          (field as any).type = FieldType.from(fieldType);
        }
      }
    });

    // Ensure metadata mappings include reference field
    const metadataField = dataset.metadata.find(m => m.name === 'reference');
    if (!metadataField && fieldNames.includes('reference')) {
      const referenceMetadata = MetadataCreation.from('reference', 'terms');
      if (referenceMetadata) {
        (dataset.selectedSubset as any).metadata.push(referenceMetadata);
      }
    }
  };

  /**
   * Get suggested field mappings from ImportHistory data
   */
  const getSuggestedFieldMappings = (importData: ImportHistoryDetails | any) => {
    // Handle both ImportHistoryDetails instance and raw data
    let rawData;
    let fieldNames: string[] = [];

    if (importData.getRawData && typeof importData.getRawData === 'function') {
      // It's an ImportHistoryDetails instance
      rawData = importData.getRawData();
      fieldNames = importData.fieldNames || [];
    } else {
      // It's raw ImportHistoryDetailsResponse data
      rawData = importData;
      fieldNames = importData.data?.schema?.fields?.map((f: any) => f.name) || [];
    }

    const builder = new ImportHistoryDatasetBuilder(rawData);

    return fieldNames.map(fieldName => ({
      source: fieldName,
      target: fieldName,
      type: builder.inferFieldType(fieldName),
      metadataType: builder.inferMetadataType(fieldName)
    }));
  };

  /**
   * Get suggested questions from ImportHistory data
   */
  const getSuggestedQuestions = (importData: ImportHistoryDetails | any) => {
    // Handle both ImportHistoryDetails instance and raw data
    let rawData;

    if (importData.getRawData && typeof importData.getRawData === 'function') {
      // It's an ImportHistoryDetails instance
      rawData = importData.getRawData();
    } else {
      // It's raw ImportHistoryDetailsResponse data
      rawData = importData;
    }

    const builder = new ImportHistoryDatasetBuilder(rawData);
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
