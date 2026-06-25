import { type IDatasetRepository } from "../services/IDatasetRepository";
import { type IDatasetsStorage } from "../services/IDatasetsStorage";

export class GetDatasetsUseCase {
  constructor(
    private readonly datasetRepository: IDatasetRepository,
    private readonly datasetStorage: IDatasetsStorage
  ) {}

  async execute() {
    const datasets = await this.datasetRepository.getAll();

    this.datasetStorage.save(datasets);
  }
}
