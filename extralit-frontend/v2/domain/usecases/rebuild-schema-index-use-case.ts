import { V2RecordRepository } from "~/v2/infrastructure/repositories/V2RecordRepository";

export class RebuildSchemaIndexUseCase {
  constructor(private readonly recordRepository: V2RecordRepository) {}

  execute(schemaId: string): Promise<number> {
    return this.recordRepository.rebuildIndex(schemaId);
  }
}
