import { type IDatasetRepository, type JobId } from "../services/IDatasetRepository";
import { DatasetCreation } from "../entities/hub/DatasetCreation";

export class UpdateDatasetUseCase {
  constructor(private readonly datasetRepository: IDatasetRepository) {}

  async execute(dataset: DatasetCreation, targetDatasetId: string): Promise<JobId> {
    return await this.datasetRepository.importDataset(targetDatasetId, dataset);
  }
}
