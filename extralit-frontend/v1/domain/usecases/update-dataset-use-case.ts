import { IDatasetRepository, JobId } from "../services/IDatasetRepository";
import { DatasetCreation } from "../entities/hub/DatasetCreation";


export class UpdateDatasetUseCase {
  constructor(private readonly datasetRepository: IDatasetRepository) { }

  async execute(dataset: DatasetCreation, targetDatasetId: string): Promise<JobId> {

    return await this.datasetRepository.import(targetDatasetId, dataset);
  }
}