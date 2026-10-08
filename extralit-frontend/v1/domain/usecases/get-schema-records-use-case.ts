import { RecordsPage } from "../entities/schema/RecordsPage";
import {
  SchemaRecordRepository,
  type GetRecordsOptions,
} from "~/v1/infrastructure/repositories/SchemaRecordRepository";

export class GetSchemaRecordsUseCase {
  constructor(private readonly recordRepository: SchemaRecordRepository) {}

  execute(schemaId: string, options: GetRecordsOptions = {}): Promise<RecordsPage> {
    return this.recordRepository.getRecords(schemaId, options);
  }
}
