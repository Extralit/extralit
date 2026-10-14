import { Dataset } from "../entities/dataset/Dataset";
import { type DatasetExportSettings } from "../entities/dataset/DatasetExport";
import { type IDatasetRepository } from "../services/IDatasetRepository";
import { type ILocalStorageService } from "../services/ILocalStorageService";

export class ExportDatasetToHubUseCase {
  constructor(
    private readonly datasetRepository: IDatasetRepository,
    private readonly localStorage: ILocalStorageService
  ) {}

  async execute(dataset: Dataset, exportSettings: DatasetExportSettings) {
    const jobId = await this.datasetRepository.export(dataset, exportSettings);

    const datasetExportJobIds: Record<string, string> = this.localStorage.get("datasetExportJobIds") ?? {};

    this.localStorage.set("datasetExportJobIds", {
      ...datasetExportJobIds,
      [dataset.id]: {
        jobId,
        datasetName: exportSettings.name,
      },
    });
  }
}
