import { RecordsPage } from "../entities/record/RecordsPage";
import { V2RecordRepository, type GetRecordsOptions } from "~/v2/infrastructure/repositories/V2RecordRepository";

export class GetSchemaRecordsUseCase {
  constructor(private readonly recordRepository: V2RecordRepository) {}

  execute(schemaId: string, options: GetRecordsOptions = {}): Promise<RecordsPage> {
    return this.recordRepository.getRecords(schemaId, options);
  }
}
