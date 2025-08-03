import { useResolve } from "ts-injecty";
import { ref } from "vue";
import { GetFirstRecordFromHub } from "~/v1/domain/usecases/get-first-record-from-hub";
import { ImportHistoryDetails } from "~/v1/domain/entities/import/ImportHistoryDetails";

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

  return {
    firstRecord,
    getFirstRecord,
  };
};
