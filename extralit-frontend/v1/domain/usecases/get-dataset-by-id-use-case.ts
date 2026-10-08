import { type IDatasetRepository } from "../services/IDatasetRepository";
import { type IDatasetStorage } from "../services/IDatasetStorage";

export class GetDatasetByIdUseCase {
  constructor(
    private readonly datasetRepository: IDatasetRepository,
    private readonly datasetStorage: IDatasetStorage
  ) {}

  async execute(id: string) {
    const dataset = await this.datasetRepository.getById(id);

    this.datasetStorage.save(dataset);
  }
}
